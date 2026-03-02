---
name: ux-design-gemini
description: "Create UX designs using memex-cli with Gemini backend. Use when (1) Generating user flows and wireframes, (2) Creating UI component specifications, (3) Designing interaction patterns, (4) Building design system documentation, (5) Producing responsive layout guides."
---

# UX Design with Gemini

Use memex-cli to leverage Gemini for UX design tasks with multimodal analysis and structured output generation.

---

## Mandatory Execution Protocol

**⚠️ CRITICAL**: Claude MUST complete ALL applicable steps BEFORE invoking memex-cli. Skipping any step is a protocol violation.

### Step 1: Scope Analysis

Analyze design task scope:

| Scope | Trigger | Action |
|-------|---------|--------|
| **Single** | 1 page/component | Execute directly |
| **Multi-page** | Multiple pages | Task decomposition |
| **Multi-stage** | Research → Define → Prototype | Dependency analysis |
| **Design System** | Complete design system | Decomposition + dependency analysis |

**Output**: Scope type with reasoning.

### Step 2: Task Decomposition (Multi-page/System MANDATORY)

**Required when**: Task involves ≥2 pages or components

Claude MUST decompose the task:
1. Identify all design deliverables
2. Split into independent design tasks
3. Assign a unique task ID to each
4. Establish dependency relationships (if any)

**Skip condition**: Only if task is truly atomic (single page, single component)

### Step 3: Dependency Analysis (Multi-stage MANDATORY)

**Required when**: Design process spans multiple stages

Design stage dependency chain:
```
Research → Define → Ideate → Prototype → Test
   ↓         ↓         ↓          ↓
personas  sitemap   userflow   wireframe
```

Claude MUST:
1. Identify design stages involved
2. Map dependencies between deliverables
3. Build execution DAG

### Step 4: Workdir Resolution (AUTO)

**Required for**: ALL tasks

Claude MUST resolve workdir to project root:

```bash
git rev-parse --show-toplevel
```

**Rule**: `workdir` = Git project root directory (absolute path)

### Step 5: Execution Plan Report (ALL Tasks)

Claude MUST report to user before execution:

```markdown
## Design Execution Plan

### Scope Analysis
- **Type**: [Single/Multi-page/Multi-stage/Design System]
- **Deliverables**: [list]

### Task Decomposition (if applicable)
| ID | Design Task | Dependencies |
|----|-------------|--------------|
| design-1 | [desc] | - |
| design-2 | [desc] | design-1 |

### Dependency Graph (if applicable)
```
Phase 1: [design-1] [design-2]
Phase 2: [design-3 depends on 1,2]
```

### Execution Summary
- **Workdir**: /path/to/project
- **Subtask count**: N
- **Parallel groups**: M
```

### Pre-Execution Checklist

Before invoking memex-cli, Claude MUST confirm:

- [ ] Scope analysis complete (Single/Multi-page/Multi-stage/System)
- [ ] (Multi-page/System) Tasks decomposed
- [ ] (Multi-stage) Dependencies analyzed
- [ ] Workdir resolved (via git root)
- [ ] Execution plan reported to user

**⛔ VIOLATION**: Directly passing multi-page/system task to Gemini without decomposition is a protocol violation.

---

## When to Use This Skill

**Choose ux-design-gemini when:**
- Creating design documentation (personas, journey maps, wireframes)
- Building design systems and component libraries
- Analyzing design screenshots for critique
- Generating structured design specifications

**Choose other skills when:**
- **Code implementation** → Use [code-with-codex](../code-with-codex/SKILL.md)
- **Complex architecture decisions** → Use Claude via memex-cli
- **Multi-backend workflows** → Combine Gemini (design) + Codex (code)

---

## Design Stages Overview

| Stage | Design Tasks | Output Examples | Gemini Strengths |
|-------|--------------|-----------------|------------------|
| **Research** | User personas, journey maps | [User Research](examples/user-research.md) | Text analysis, structured output |
| **Define** | Information architecture, site maps | [IA Examples](examples/information-architecture.md) | Hierarchical structure generation |
| **Ideate** | User flows, concept descriptions | See Quick Start below | Rapid iteration on concepts |
| **Prototype** | Wireframe specs, mockups, design systems | [Wireframes](examples/wireframes-mockups.md), [Components](examples/component-systems.md) | Detailed specifications |
| **Test** | Design reviews, accessibility audits | [Design Review](examples/design-review.md) | **Image analysis** for visual critique |

➜ **Complete workflow guide:** [references/design-workflow.md](references/design-workflow.md)

---

## Quick Start

### Generate User Flow

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: user-flow
backend: gemini
workdir: /path/to/project
---CONTENT---
Design a complete user shopping flow for an e-commerce app, including browsing, adding to cart, checkout, and payment
---END---
EOF
```

### Create Wireframe Spec

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: wireframe
backend: gemini
workdir: /path/to/project
---CONTENT---
Create wireframe specifications for login and registration pages, including layout, component placement, and interaction states
---END---
EOF
```

### Design Component System

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: component-system
backend: gemini
workdir: /path/to/project
---CONTENT---
Design a mobile UI component specification including buttons, input fields, cards, and navigation bar style definitions
---END---
EOF
```

---

## Common UX Tasks

### User Research

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: personas
backend: gemini
---CONTENT---
Create 3 user personas for a fitness app, including goals, pain points, and usage scenarios
---END---
EOF
```

➜ **More examples:** [examples/user-research.md](examples/user-research.md)

---

### Information Architecture

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: sitemap
backend: gemini
---CONTENT---
Design a sitemap and navigation structure for a SaaS project management tool
---END---
EOF
```

➜ **More examples:** [examples/information-architecture.md](examples/information-architecture.md)

---

### Wireframes & Mockups

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: wireframe-specs
backend: gemini
---CONTENT---
Create low-fidelity wireframe specs for key pages of a mobile food delivery app (home, restaurant detail, shopping cart)
---END---
EOF
```

➜ **More examples:** [examples/wireframes-mockups.md](examples/wireframes-mockups.md)

---

### Component Systems

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: design-system
backend: gemini
---CONTENT---
Create design system documentation: color system, typography specs, spacing system, and component library
---END---
EOF
```

➜ **More examples:** [examples/component-systems.md](examples/component-systems.md)

---

### Design Review

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: heuristic-eval
backend: gemini
files: ./dashboard.png
files-mode: embed
---CONTENT---
Evaluate this dashboard design using Nielsen's 10 Heuristics
---END---
EOF
```

➜ **More examples:** [examples/design-review.md](examples/design-review.md)

---

## Multimodal Capabilities

**Gemini's unique strength:** Analyze design screenshots for visual critique.

### Upload Design for Review

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: design-critique
backend: gemini
files: ./mockup.png
files-mode: embed        # Required for image analysis
---CONTENT---
Review this design mockup:
1. Is the visual hierarchy clear?
2. Does the color contrast meet WCAG AA standards?
3. Is the component layout reasonable?
4. Is the whitespace and spacing appropriate?
---END---
EOF
```

**Supported formats:** PNG, JPG, WEBP (< 5MB recommended)

### Compare Design Versions

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: version-compare
backend: gemini
files: ./v1-home.png, ./v2-home.png
files-mode: embed
---CONTENT---
Compare these two versions of the homepage design, analyze improvements and potential issues
---END---
EOF
```

### Competitive Analysis

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: competitive-analysis
backend: gemini
files: ./our-app.png, ./competitor-a.png, ./competitor-b.png
files-mode: embed
---CONTENT---
Perform a comparative analysis of our app against competitors: layout, visual style, and interaction patterns
---END---
EOF
```

**Use cases:**
- Design critique and feedback
- Accessibility audit (color contrast check)
- Competitive screenshot analysis
- Design system compliance verification

➜ **Advanced image analysis techniques:** [references/multimodal-tips.md](references/multimodal-tips.md)

---

## Advanced Workflows

For multi-task workflows, parallel execution, and resume functionality, refer to memex-cli skill:

- **Multi-task DAG workflows:** [memex-cli/references/advanced-usage.md](../memex-cli/references/advanced-usage.md)
- **Parallel execution patterns:** [memex-cli/examples/parallel-tasks.md](../memex-cli/examples/parallel-tasks.md)
- **Resume interrupted runs:** [memex-cli/examples/resume-workflow.md](../memex-cli/examples/resume-workflow.md)

**Example multi-stage workflow:**

```bash
memex-cli run --stdin <<'EOF'
---TASK---
id: research
backend: gemini
---CONTENT---
User research
---END---

---TASK---
id: architecture
backend: gemini
dependencies: research
---CONTENT---
Information architecture design
---END---

---TASK---
id: wireframe
backend: gemini
dependencies: architecture
---CONTENT---
Wireframe specifications
---END---
EOF
```

See [references/design-workflow.md](references/design-workflow.md) for complete design process with DAG examples.

---

## Quick Reference

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique task identifier |
| `backend` | `gemini` |
| `workdir` | Working directory path |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `dependencies` | - | Task IDs for sequential execution |
| `timeout` | 1800 | Seconds (30 minutes) |
| `files` | - | Design files to analyze (PNG, JPG) |
| `files-mode` | auto | `embed` (required for image analysis) |

---

## Additional Resources

### Progressive Disclosure Documentation

- **[HOW_TO_USE.md](HOW_TO_USE.md)** - Complete usage guide
  - When to use this skill
  - Gemini vs other backends
  - Integration with design tools
  - Workflow recommendations

- **[references/design-principles.md](references/design-principles.md)** - UX design fundamentals
  - UX methodologies (Design Thinking, UCD)
  - Nielsen's 10 heuristics
  - Mobile design guidelines (iOS HIG, Material Design)
  - Accessibility standards (WCAG 2.1)
  - Visual hierarchy and color theory

- **[references/design-workflow.md](references/design-workflow.md)** - Complete design process
  - 5-stage workflow (Research → Define → Ideate → Prototype → Test)
  - Deliverables by stage
  - DAG workflow examples
  - Iteration and feedback loops
  - Handoff to development

- **[references/multimodal-tips.md](references/multimodal-tips.md)** - Image analysis techniques
  - File format and size recommendations
  - Design critique prompt templates
  - Multi-image comparison analysis
  - Screenshot preparation tips

### Detailed Examples

- **[examples/user-research.md](examples/user-research.md)** - Personas, journey maps, competitive analysis
- **[examples/information-architecture.md](examples/information-architecture.md)** - Site maps, navigation, content hierarchy
- **[examples/wireframes-mockups.md](examples/wireframes-mockups.md)** - Lo-fi wireframes, hi-fi mockups, responsive layouts
- **[examples/component-systems.md](examples/component-systems.md)** - Design systems, component libraries, style guides
- **[examples/design-review.md](examples/design-review.md)** - Heuristic evaluations, accessibility audits, visual critiques

---

## Tips

1. **Use structured prompts**
   - Specify output format (Markdown tables, ASCII diagrams)
   - Provide context (target users, design constraints)
   - Include specific requirements (WCAG compliance, iOS HIG)

2. **Leverage multimodal analysis**
   - Upload design screenshots for visual feedback
   - Compare multiple design versions
   - Analyze competitor interfaces
   - Use `files-mode: embed` for image analysis

3. **Break down large projects**
   - Use dependencies for sequential stages
   - Parallelize independent pages/components
   - See [design workflow guide](references/design-workflow.md)

4. **Integrate with design tools**
   - Export from Figma/Sketch as PNG
   - Use Gemini to generate component specs
   - Create handoff documentation for developers

5. **Follow design principles**
   - Reference [design principles guide](references/design-principles.md)
   - Apply Nielsen's heuristics for evaluation
   - Ensure WCAG 2.1 Level AA compliance

---

## SKILL Reference

- [skills/memex-cli/SKILL.md](../memex-cli/SKILL.md) - Memex CLI full documentation
- [HOW_TO_USE.md](HOW_TO_USE.md) - Detailed usage guide for this skill
