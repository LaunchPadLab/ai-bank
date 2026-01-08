---
description: Nova project workflow rules for AI-assisted development
globs:
alwaysApply: true
---
---
description: Nova project workflow rules for AI-assisted development
globs:
alwaysApply: true
---

# Nova Project Rules

You are working in a Nova project that follows a structured product development workflow from abstract ideas to concrete implementation.

## Project Structure
- `shape/` - Product documentation (no code here)
  - `1_big-picture/` - PRD, flowchart
  - `2_user-stories/` - User stories and their acceptance criteria
  - `3_design-system/` - UI/UX standards and components
  - `4_tasks/` - Implementation tasks with progress tracking
- `code/` - Application implementation

## Git Repository Structure
- The project uses a mono repo structure with a single git repository at the project root
- Both `shape/` and `code/` directories are tracked in the same repository
- This allows for atomic commits that include both documentation updates and code changes

## Workflow
1. **Big Picture**: Define PRD and flowchart
2. **User Stories**: Break down into specific user needs
3. **Design System**: Establish visual language
4. **Tasks**: Create actionable implementation steps
5. **Code**: Build features following the tasks

## Key Rules

### When in shape/ (Documentation)
- Don't write code - documentation only
- Use Mermaid for diagrams
- Reference previous sections for traceability
- Delete the example.md file in the current section once a real file is generated in that specific section (e.g., delete example.md in 1_big-picture/ when prd.md is created)
- Do not advance to the next section until told to do so

### When in code/ (Implementation)
- Always create a new branch before starting a new task
- Review shape/ documentation first
- Follow tasks in shape/4_tasks/
- When any task or subtask is completed, check it off in the appropriate task file
- After completing a subtask, commit your work to the new branch. Before committing your work, please look for opportunities to refactor/improve the code you wrote for better readability and/or performance (e.g. small methods, squash n+1 queries, etc.)
- Use the `gh` CLI tool to open a new PR and in the body/description of the PR include the content from the task


### Code Quality Standards
- Rails conventions with minitest
- Keep methods under 10 lines (use POROs if needed)
- Name POROs as verbs with single `call` method
- Components should follow design system
- Write E2E tests with Capybara

### Task Management
- Work through tasks sequentially in /tasks
- If there are any remaining Open Questions, prompt the user if the question is answered, and if so, to update the task
- Whenever you complete a task/subtask, check it off
- Update file tracking tables (⏳ → ✅)

### Change Requests
- When asked to make a change to the code, first analyze shape/ and update any impacted documentation

## Remember
- Keep things simple unless specified otherwise
- Be concise and do not repeat yourself
- Maintain documentation-to-code traceability
- Focus on user value in every decision
- This is an iterative process - expect refinements
