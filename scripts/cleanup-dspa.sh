#!/bin/bash
#
# cleanup-dspa.sh - Clean up Data Science Pipelines Application (DSPA) resources
#
# This script deletes all pipeline runs, workflows, and optionally S3 artifacts
# for a given namespace to force fresh pipeline executions without cache.
#
# Usage:
#   ./cleanup-dspa.sh <namespace>
#   ./cleanup-dspa.sh <namespace> --delete-s3-artifacts
#

set -e

NAMESPACE="${1:-rhoai-playground}"
DELETE_S3="${2}"

echo "============================================"
echo "DSPA Cleanup Script"
echo "============================================"
echo "Namespace: $NAMESPACE"
echo ""

# Check if namespace exists
if ! oc get namespace "$NAMESPACE" &>/dev/null; then
    echo "ERROR: Namespace '$NAMESPACE' does not exist"
    exit 1
fi

# Switch to namespace
oc project "$NAMESPACE" || exit 1

echo "1. Deleting all Argo Workflows..."
WORKFLOW_COUNT=$(oc get workflows --no-headers 2>/dev/null | wc -l)
if [ "$WORKFLOW_COUNT" -gt 0 ]; then
    oc delete workflows --all
    echo "   Deleted $WORKFLOW_COUNT workflows"
else
    echo "   No workflows found"
fi

echo ""
echo "2. Deleting KFP Pipeline Runs via API..."

# Get DSP API URL
DSP_URL=$(oc get route ds-pipeline-dspa -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

if [ -z "$DSP_URL" ]; then
    echo "   WARNING: DSP route not found, skipping API cleanup"
else
    # Get service account token
    SA_TOKEN=$(oc create token pipeline 2>/dev/null || oc sa get-token pipeline 2>/dev/null || echo "")

    if [ -z "$SA_TOKEN" ]; then
        echo "   WARNING: Could not get service account token, skipping API cleanup"
    else
        # List all runs
        RUN_LIST=$(curl -sk -H "Authorization: Bearer $SA_TOKEN" \
            "https://$DSP_URL/apis/v2beta1/runs" 2>/dev/null)

        RUN_IDS=$(echo "$RUN_LIST" | jq -r '.runs[]?.run_id // empty' 2>/dev/null)

        if [ -z "$RUN_IDS" ]; then
            echo "   No pipeline runs found in DSP"
        else
            RUN_COUNT=$(echo "$RUN_IDS" | wc -l)
            echo "   Found $RUN_COUNT pipeline runs"

            # Delete each run
            for RUN_ID in $RUN_IDS; do
                echo "   Deleting run: $RUN_ID"
                curl -sk -X DELETE -H "Authorization: Bearer $SA_TOKEN" \
                    "https://$DSP_URL/apis/v2beta1/runs/$RUN_ID" 2>/dev/null || true
            done

            echo "   Deleted $RUN_COUNT pipeline runs"
        fi
    fi
fi

echo ""
echo "3. Cleaning up PipelineRun resources..."
PIPELINERUN_COUNT=$(oc get pipelinerun --no-headers 2>/dev/null | wc -l)
if [ "$PIPELINERUN_COUNT" -gt 0 ]; then
    oc delete pipelinerun --all
    echo "   Deleted $PIPELINERUN_COUNT pipeline runs"
else
    echo "   No pipeline runs found"
fi

echo ""
echo "4. Cleaning up TaskRun resources..."
TASKRUN_COUNT=$(oc get taskrun --no-headers 2>/dev/null | wc -l)
if [ "$TASKRUN_COUNT" -gt 0 ]; then
    oc delete taskrun --all
    echo "   Deleted $TASKRUN_COUNT task runs"
else
    echo "   No task runs found"
fi

echo ""
echo "5. Cleaning up completed/failed pods..."
POD_COUNT=$(oc get pods --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
if [ "$POD_COUNT" -gt 0 ]; then
    oc delete pods --field-selector=status.phase!=Running
    echo "   Deleted $POD_COUNT pods"
else
    echo "   No completed/failed pods found"
fi

# Optional S3 cleanup
if [ "$DELETE_S3" == "--delete-s3-artifacts" ]; then
    echo ""
    echo "6. Cleaning up S3 artifacts..."

    # Get MinIO credentials from secret
    S3_ACCESS_KEY=$(oc get secret dspa-pipelines-connection-secret -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' 2>/dev/null | base64 -d)
    S3_SECRET_KEY=$(oc get secret dspa-pipelines-connection-secret -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' 2>/dev/null | base64 -d)
    S3_ENDPOINT=$(oc get secret dspa-pipelines-connection-secret -o jsonpath='{.data.endpoint}' 2>/dev/null | base64 -d)
    S3_BUCKET="rhoai-playground-dspa-pipelines-connection-secret"

    if [ -n "$S3_ACCESS_KEY" ] && [ -n "$S3_SECRET_KEY" ]; then
        # Install mc (MinIO Client) if not available
        if ! command -v mc &>/dev/null; then
            echo "   WARNING: 'mc' (MinIO Client) not found. Install from https://min.io/docs/minio/linux/reference/minio-mc.html"
            echo "   Skipping S3 cleanup"
        else
            # Configure mc alias
            mc alias set dspa-minio "http://$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" --insecure

            # Remove all objects in the bucket
            echo "   Removing all objects from bucket: $S3_BUCKET"
            mc rm --recursive --force "dspa-minio/$S3_BUCKET" --insecure || echo "   WARNING: Failed to remove S3 objects"

            echo "   S3 artifacts cleaned"
        fi
    else
        echo "   WARNING: Could not retrieve S3 credentials, skipping S3 cleanup"
    fi
else
    echo ""
    echo "6. Skipping S3 cleanup (use --delete-s3-artifacts to clean S3)"
fi

echo ""
echo "============================================"
echo "Cleanup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Trigger a new pipeline run"
echo "  2. All components will execute fresh without cache"
echo ""
