# Integrated Prompt Studio domain

Prompt Studio is one authoring tool. Its panels are views of one project, not independent tools or documents.

## Canonical hierarchy

```text
Project
├── reusable entities
│   ├── Subjects
│   ├── Environments
│   └── Media assets and physical sources
├── global Look
└── Generations
    └── ordered Shots
```

A **Shot** is one continuous visual block between cuts and maps one-to-one to `shot_plan.shots[]`.
A **Cut** is only the transition into a Shot (`transitionIn` / `cutContext`). `Scene` is not a stored
entity and must not be used as a synonym for Shot. A future Scene concept would require its own schema
and would group multiple Shots explicitly.

## Ownership and scope

| Fact | Canonical owner | Scope |
|---|---|---|
| Subject name and identity gallery | Media Project Subject | Project default |
| Subject default voice | Media Project Subject | Project default |
| Appearance definitions | Media Project Subject | Reusable definition |
| Environment geometry, views and states | Media Project Environment | Reusable definition |
| Subject presence | Shot Plan Shot | This Shot |
| Environment and selected views | Shot Plan Shot | This Shot |
| Action, dialogue and beats | Shot Plan Shot | This Shot |
| Staging and camera | Shot Plan Shot | This Shot |
| Performance, soundtrack, continuity and camera references | `shot.referenceUses` | This Shot |
| Generation bindings and H3 slots | Media Project Generation | This Generation |
| Physical file provenance | Reference source storage | Project asset |
| Creative treatment and global cinematography | Look documents | Project default |

The UI must label inherited values as **Project default** and Shot relationships as **This Shot**.
Changing a Project default from Compose must warn that every inheriting Shot is affected. Detaching a
Shot relationship must never delete the reusable Subject, Environment view or Media asset.

## Integrated surfaces

- **Compose** owns the ordered Shot workflow. Build, Stage and Camera are contextual modes of the same
  selected Shot; the Shot strip remains visible in every mode.
- **Cast & Places** creates and maintains reusable Subjects and Environments. It does not decide Shot
  presence or the background selected for a Shot.
- **Media** imports, replaces, previews and audits physical assets. Semantic placement happens from the
  target in Compose or from a reusable entity in Cast & Places.
- **Look** owns global creative defaults. Compose only displays their inherited summary and links back.
- **Review** shows diagnostics, compiled prompt/reference preview, quotas and readiness.

Legacy routes such as `shots`, `staging`, `camera`, `subjects` and `environments` remain valid deep links,
but resolve into the integrated surface and shared Shot selection rather than appearing as duplicate tabs.

## Compilation invariant

The same Project, Generation, Shot and reference assignments must produce both:

1. the authoritative natural-language reference context sent to the LLM; and
2. the ordered picture, video and audio outputs sent to H3.

No frontend-only reconstruction may declare the project ready. Readiness must ultimately come from the
same Python compiler used during execution and must include its digest.
