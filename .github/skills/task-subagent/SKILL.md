---
name: task-subagent
description: Use this skill when deciding whether to delegate work to sub-agents, how to craft effective prompts for them, and when to handle tasks directly. Maximizes efficiency through proper task delegation.
---

# Task Sub-Agent Skill

A comprehensive guide to effectively using sub-agents (via the `task` tool) in GitHub Copilot CLI.

> **Note for GitHub Copilot Chat Users**: This skill provides delegation workflow guidance. In VS Code, use the available tools like `@terminal`, `@workspace`, and inline chat for similar parallelization.

## When to Use This Skill

Invoke this skill when:
- Deciding whether to delegate work or do it yourself
- Crafting prompts for sub-agents
- Managing multiple parallel investigations
- Determining which agent type to use
- Reviewing sub-agent results and integrating them

## Core Principle: Delegate Strategically

**DO delegate** when:
- The task naturally decomposes into independent research threads
- Multiple files, modules, or services need analysis in parallel
- A complex investigation crosses many areas of the codebase
- You need a fresh perspective (code-review agent)
- Tasks are side-effect-free and can run in background

**DO NOT delegate** when:
- It's a simple lookup (specific file, symbol, or known location)
- You need immediate results for the next step
- The task requires sequential reasoning building on previous steps
- You're editing files you already know well
- The cost of context-switching exceeds the benefit

## Available Agent Types

| Agent Type | Purpose | When to Use |
|-----------|---------|-------------|
| **explore** | Fast codebase exploration and research | Many independent research threads, cross-cutting investigations, multiple unrelated questions |
| **task** | Executing commands with verbose output | Tests, builds, lints, dependency installs. Returns brief summary on success, full output on failure. |
| **general-purpose** | Complex multi-step tasks | Full toolset required, high-quality reasoning, multi-phase implementation |
| **code-review** | Review code changes | Staged/unstaged changes, branch diffs. Surfaces only genuine bugs, security issues, logic errors. |
| **research** | External research | Searches GitHub repos, fetches files, verifies claims, reports findings with citations |

## Crafting Effective Sub-Agent Prompts

### Critical Rules

1. **Provide COMPLETE context** - Sub-agents are stateless. Include every detail needed:
   - File paths
   - Function names
   - Error messages
   - Expected vs actual behavior
   - Relevant code snippets

2. **Be SPECIFIC about the task** - Not "check the code" but "identify why the `authMiddleware` function returns 403 for valid tokens in `src/middleware/auth.ts`"

3. **Specify the OUTPUT format** - Tell the agent exactly what to return:
   - "Report back with: file path, line number, and suggested fix"
   - "Return a JSON object with keys: issue, location, severity, fix"

4. **Set BOUNDARIES** - Define what's in scope:
   - "Only look at files in src/auth/"
   - "Do NOT modify any files, only report findings"

### Example: Good vs Bad Prompts

❌ **BAD**: "Check the API code for issues"

✅ **GOOD**: "Review the following files for memory leaks in async handlers:
- src/routes/users.ts (lines 45-80)
- src/routes/orders.ts (lines 120-150)

Look specifically for:
1. Event listeners not removed
2. Unclosed database connections
3. Promise chains without catch blocks

Return a markdown list with: file, line, issue description, and fix suggestion."

## Parallel Execution Strategy

### Launch Multiple Agents in Parallel

When you have independent tasks, launch them simultaneously:

```
Agent 1: Explore auth module structure
Agent 2: Explore database schema  
Agent 3: Explore frontend state management
```

**Do NOT** wait for Agent 1 to finish before launching Agent 2.

### Batch Related Questions

Group related questions into a single explore agent call rather than multiple separate calls.

### Do NOT Duplicate Work

Once a sub-agent has reported on a scope, do NOT investigate the same scope yourself. Trust the results or ask the agent for clarification.

## Managing Background Agents

### For Work You Need Later

1. Launch background agent for the task
2. Tell the user you're waiting
3. End your response (a completion notification arrives automatically)
4. When notified, use `read_agent` with `wait: true` to retrieve results

### For Fire-and-Forget Tasks

If results aren't needed immediately:
- Launch and continue with other work
- Check results when convenient

## Integrating Sub-Agent Results

### Synthesize, Don't Just Report

When sub-agents return results:
1. **Synthesize findings** into coherent recommendations
2. **Cross-reference** results from multiple agents
3. **Prioritize** issues by severity and impact
4. **Propose concrete next steps**

### Example Integration

```
Agent 1 found: 3 unused imports in src/utils/
Agent 2 found: 2 missing error handlers in src/api/
Agent 3 found: Test coverage gap in auth module

Synthesis:
- Priority 1: Fix missing error handlers (production risk)
- Priority 2: Add auth tests (quality gate)
- Priority 3: Clean up imports (tech debt)
```

## Error Handling

### When a Sub-Agent Fails

1. **Read the error output** carefully
2. **Re-prompt with corrections** - often the issue was ambiguous instructions
3. **Escalate to general-purpose** if task agent keeps failing
4. **Do it yourself** if the agent fails repeatedly

### Common Failure Modes

- **Incomplete context**: Agent lacks file paths or code needed
- **Overly broad scope**: Task too large for a single agent
- **Ambiguous instructions**: Multiple interpretations possible
- **Missing permissions**: Agent can't access required files/tools

## Verification Loop

After integrating sub-agent work:

1. **Verify the changes work** - run tests, builds, type checks
2. **Review diff** - ensure only intended changes were made
3. **Check for side effects** - sub-agents may have modified files unexpectedly
4. **Validate output format** - ensure results match requested format

## Anti-Patterns to Avoid

### ❌ Speculative Background Agents

Don't launch explore agents "just in case." They consume resources and often finish after you've already found the answer yourself.

### ❌ Recursive Delegation

Don't have a sub-agent delegate to another sub-agent unless absolutely necessary. You lose oversight and context.

### ❌ Micro-Management

Don't launch a sub-agent for tasks you can complete in a single tool call (e.g., reading one file, running one grep).

### ❌ Ignoring Results

Always read and act on sub-agent results. Background agents exist to inform your next steps.

## Success Metrics

- Tasks that benefit from parallelization are delegated
- Sub-agent prompts are specific and complete
- Results are synthesized, not copy-pasted
- No duplicate investigations
- Background tasks don't block critical path work
- Failed agents are retried or escalated appropriately

---

**Remember**: Sub-agents multiply your capabilities but require thoughtful delegation. A well-crafted prompt to a sub-agent is worth more than five poorly specified ones.
