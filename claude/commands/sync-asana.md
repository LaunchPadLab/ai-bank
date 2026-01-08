# Sync User Stories to Asana (Template)

This command syncs user stories from a folder structure to Asana tasks. It finds user stories without an Asana ID, creates tasks in Asana, and updates the source files with the new Asana task IDs.

## Configuration Required

Before using this command, create a configuration file at `.claude/config/asana.json`:

```json
{
  "workspace_id": "YOUR_WORKSPACE_ID",
  "project_id": "YOUR_PROJECT_ID",
  "user_stories_path": "path/to/user-stories",
  "story_id_field": "**Story ID:**",
  "asana_id_field": "**Asana ID:**",
  "epic_folders": [],
  "skip_patterns": ["*_epic_details.md", "*_overview.md"]
}
```

**Configuration Fields:**
- `workspace_id`: Your Asana workspace GID (find in Asana URL or API)
- `project_id`: The Asana project GID to sync tasks to
- `user_stories_path`: Relative path to your user stories directory
- `story_id_field`: The markdown field name for story IDs in your files
- `asana_id_field`: The markdown field name for Asana IDs (will be added by this command)
- `epic_folders`: Array of valid epic/folder names (leave empty to auto-detect)
- `skip_patterns`: File patterns to skip (e.g., epic overview files)

## Usage

Run this command and specify which folder to sync. The command will prompt for the folder name if not provided.

## Steps to Execute

### Step 1: Load Configuration

1. Read `.claude/config/asana.json` to get project-specific settings
2. If the config file doesn't exist, prompt the user to create one with:
   - Asana workspace ID
   - Asana project ID
   - User stories directory path

### Step 2: Identify the Target Folder

Ask the user which folder to sync. Valid options are:
- Subdirectories in the configured `user_stories_path`
- Or values from `epic_folders` array if configured

### Step 3: Find User Stories Without Asana IDs

1. List all markdown files in the specified folder: `{user_stories_path}/{folder_name}/`
2. Skip files matching patterns in `skip_patterns`
3. Read each user story file
4. Check if the file contains the configured `asana_id_field` - if not, it needs to be synced

### Step 4: Parse User Story Content

For each user story file without an Asana ID, extract:

1. **Story ID**: From the configured `story_id_field` line (e.g., "US-01")

2. **Estimate**: Look for estimate fields like:
   - `**Estimate:**`
   - `**Estimate (Dev Days):**`
   - `**Story Points:**`

3. **Title**: From the H1 heading, extract just the story name
   - Example: `# User Story: Feature Name` → `Feature Name`
   - Or: `# US-01: Feature Name` → `Feature Name`

4. **User Story Statement**: The "As a / I want / So that" statement
   - Look for lines starting with `**As a**`, `**I want**`, `**So that**`
   - Combine into a single statement

5. **Acceptance Criteria**: From the `## Acceptance Criteria` section
   - Extract all bullet points/checklist items

6. **Questions**: From the `## Questions` or `## Open Questions` section
   - Extract all bullet points/checklist items

7. **Design References**: From the `## Design References` or `## Designs` section
   - Extract all markdown links (especially Figma, Miro, etc.)
   - Skip placeholder entries like "TBD" or "None"

### Step 5: Check for Existing Task in Asana

Before creating a new task, check if one already exists:

1. **Search by Story ID** using `mcp_asana_asana_search_tasks`:
   ```
   workspace: "{workspace_id}"
   text: "{Story ID}"
   projects_any: "{project_id}"
   ```

2. **If no match, search by title** using `mcp_asana_asana_search_tasks`:
   ```
   workspace: "{workspace_id}"
   text: "{Story Title}"
   projects_any: "{project_id}"
   ```

3. Handle search results:
   - **If task found**:
     - Skip creating a new task
     - Use existing task's GID to update the source file
     - Update existing task title to include Story ID if missing
     - Report: `↔ {Story ID} already exists in Asana (ID: {gid})`
   - **If no match found**: Proceed to create the task

### Step 6: Create Asana Task

Use `mcp_asana_asana_create_task` with:

```
Title: {Story ID} {Story Title}

Description (notes):
USER STORY
As a {user type}
I want {goal}
So that {benefit}

ESTIMATE
{estimate value}

ACCEPTANCE CRITERIA
- {criterion 1}
- {criterion 2}

DESIGNS
- {Link Name}: {URL}
(or "None" if no design links)

QUESTIONS
- {question 1}
- {question 2}
(or "None" if no questions)
```

**Task Parameters:**
- `project_id`: From config
- `name`: Story ID + title
- `notes`: Plain text description (avoid `html_notes`)

### Step 7: Update Source File

After creating or finding an Asana task, add the Asana ID to the source file:

1. Find the line with the configured `story_id_field`
2. Add a new line directly after: `{asana_id_field} {task_gid}`

**Example:**
```markdown
**Story ID:** US-01
**Asana ID:** 1234567890123456

**As a** user...
```

### Step 8: Report Results

After processing all files, report:
- Number of user stories found
- Number already synced (had Asana IDs)
- Number of new tasks created
- Number of existing tasks linked
- Any errors encountered

## Example Execution

```
User: Sync the authentication folder to Asana

Agent:
1. Loading config from .claude/config/asana.json
2. Scanning {user_stories_path}/authentication/
3. Found 9 user story files, 3 already have Asana IDs
4. Processing 6 user stories without Asana IDs...

   ✓ US-01 Passwordless Login → Created (Asana ID: 1234567890123456)
   ↔ US-02 Request Access → Already exists (ID: 1234567890123457)
   ✓ US-03 Password Reset → Created (Asana ID: 1234567890123458)
   ...

5. Summary:
   - 4 new tasks created
   - 2 existing tasks linked
   - 6 user story files updated with Asana IDs
```

## Adapting to Your Project

### Different File Formats

If your user stories use a different format, adjust parsing in Step 4:

**Format A - YAML Frontmatter:**
```yaml
---
id: US-01
title: Feature Name
estimate: 3
---
```

**Format B - Simple Markdown:**
```markdown
# US-01: Feature Name

## Description
As a user, I want...
```

**Format C - Structured Fields:**
```markdown
| Field | Value |
|-------|-------|
| ID | US-01 |
| Title | Feature Name |
```

### Different Folder Structures

Common patterns:
- `docs/user-stories/{epic}/`
- `specs/stories/{feature}/`
- `requirements/{module}/`
- Single flat folder with all stories

### Custom Asana Fields

If you use custom fields in Asana, extend the task creation:
```
custom_fields: {
  "custom_field_gid": "value"
}
```

## Notes

- Always test with a single story before bulk syncing
- The command only processes individual user stories, not overview/epic files
- Existing Asana IDs in files are preserved (never overwritten)
- Duplicate detection uses both Story ID and title matching
- Configure `skip_patterns` to exclude non-story files
