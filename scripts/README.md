# Generate Diffs Script

This script compares the current branch to the main branch and generates individual diff files for each changed file.

## Usage

```bash
# Compare current branch to main (default)
./scripts/generate-diffs.sh

# Compare current branch to a specific branch
./scripts/generate-diffs.sh develop
```

## Output

The script creates:
- Individual diff files in `.tmp/diff_<filename>.txt` for each changed file
- A summary file at `.tmp/diff_summary.txt` with an overview of all changes

## Features

- **Automatic cleanup**: Removes old diff files before generating new ones
- **Safe filenames**: Converts file paths to safe filenames for output files
- **New file detection**: Handles files that are new in the current branch
- **Deleted file handling**: Skips files that have been deleted
- **Colored output**: Uses colors for better readability in terminal
- **Comprehensive summary**: Generates a summary with statistics and file listings

## Example Output Structure

```
.tmp/
├── diff_summary.txt                                    # Overall summary
├── diff_apps_frontend_src_App_tsx.txt                 # Frontend App component
├── diff_apps_backend_src_main_py.txt                  # Backend main file
├── diff_docker-compose_dev_yml.txt                    # Docker dev config
└── ... (one file per changed file)
```

## Use Cases

- **Code review preparation**: Generate diffs for review before creating PR
- **Documentation**: Create comprehensive change documentation
- **Backup**: Save current changes before major refactoring
- **Analysis**: Analyze changes across entire codebase
- **Sharing**: Share specific file changes with team members

## Notes

- The `.tmp/` directory is automatically ignored by git (added to .gitignore)
- Script uses `git merge-base` to find the proper comparison point
- Handles both local and remote branch comparisons
- Safe to run multiple times (cleans up previous runs)
