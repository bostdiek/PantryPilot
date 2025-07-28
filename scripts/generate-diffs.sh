#!/bin/bash

# Script to generate diff files for all changed files between current branch and main
# Output: .tmp/diff_<filename>.txt for each changed file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get current branch name
CURRENT_BRANCH=$(git branch --show-current)
TARGET_BRANCH=${1:-main}

print_info "Comparing branch '$CURRENT_BRANCH' to '$TARGET_BRANCH'"

# Ensure we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository!"
    exit 1
fi

# Check if target branch exists
if ! git show-ref --verify --quiet refs/heads/$TARGET_BRANCH && ! git show-ref --verify --quiet refs/remotes/origin/$TARGET_BRANCH; then
    print_error "Target branch '$TARGET_BRANCH' does not exist!"
    exit 1
fi

# Create .tmp directory if it doesn't exist
mkdir -p .tmp

# Clean up any existing diff files
rm -f .tmp/diff_*.txt

print_info "Cleaning up previous diff files..."

# Get list of changed files between current branch and target branch
print_info "Finding changed files..."

# Use origin/main if local main doesn't exist, otherwise use local main
if git show-ref --verify --quiet refs/heads/$TARGET_BRANCH; then
    COMPARE_TARGET="$TARGET_BRANCH"
else
    COMPARE_TARGET="origin/$TARGET_BRANCH"
fi

# Get the merge base to compare from the common ancestor
MERGE_BASE=$(git merge-base HEAD $COMPARE_TARGET 2>/dev/null || echo $COMPARE_TARGET)

# Get list of changed files (added, modified, deleted)
CHANGED_FILES=$(git diff --name-only $MERGE_BASE..HEAD)

if [ -z "$CHANGED_FILES" ]; then
    print_warning "No changes found between '$CURRENT_BRANCH' and '$TARGET_BRANCH'"
    exit 0
fi

print_info "Found $(echo "$CHANGED_FILES" | wc -l) changed files"

# Counter for processed files
PROCESSED=0
SKIPPED=0

# Process each changed file
while IFS= read -r file; do
    if [ -z "$file" ]; then
        continue
    fi

    # Skip if file doesn't exist (might be deleted)
    if [ ! -f "$file" ]; then
        print_warning "Skipping deleted file: $file"
        ((SKIPPED++))
        continue
    fi

    # Generate safe filename for diff output
    # Replace path separators and special characters with underscores
    SAFE_FILENAME=$(echo "$file" | sed 's/[\/\.]/_/g' | sed 's/[^a-zA-Z0-9_-]/_/g')
    DIFF_FILE=".tmp/diff_${SAFE_FILENAME}.txt"

    print_info "Processing: $file -> $DIFF_FILE"

    # Generate diff and save to file
    {
        echo "# Diff for: $file"
        echo "# Branch: $CURRENT_BRANCH vs $TARGET_BRANCH"
        echo "# Generated: $(date)"
        echo "# =============================================="
        echo ""

        # Check if file exists in target branch
        if git cat-file -e $MERGE_BASE:$file 2>/dev/null; then
            # File exists in both branches - show diff
            git diff $MERGE_BASE..HEAD -- "$file"
        else
            # File is new in current branch
            echo "# This is a new file in $CURRENT_BRANCH"
            echo "# Showing full content:"
            echo ""
            echo "--- /dev/null"
            echo "+++ b/$file"
            echo "@@ -0,0 +1,$(wc -l < "$file") @@"
            sed 's/^/+/' "$file"
        fi
    } > "$DIFF_FILE"

    print_success "Created diff: $DIFF_FILE"
    ((PROCESSED++))

done <<< "$CHANGED_FILES"

# Generate summary file
SUMMARY_FILE=".tmp/diff_summary.txt"
{
    echo "# Diff Summary"
    echo "# =============================================="
    echo "# Branch: $CURRENT_BRANCH vs $TARGET_BRANCH"
    echo "# Generated: $(date)"
    echo "# Processed: $PROCESSED files"
    echo "# Skipped: $SKIPPED files"
    echo "# =============================================="
    echo ""
    echo "## Changed Files:"
    echo "$CHANGED_FILES"
    echo ""
    echo "## Generated Diff Files:"
    ls -la .tmp/diff_*.txt 2>/dev/null || echo "None"
} > "$SUMMARY_FILE"

print_success "Generated summary: $SUMMARY_FILE"

# Final summary
echo ""
print_success "Diff generation complete!"
print_info "📊 Summary:"
echo "   • Processed: $PROCESSED files"
echo "   • Skipped: $SKIPPED files"
echo "   • Output directory: .tmp/"
echo "   • Summary file: $SUMMARY_FILE"

# List generated files
if [ $PROCESSED -gt 0 ]; then
    echo ""
    print_info "📁 Generated diff files:"
    ls -la .tmp/diff_*.txt
fi
