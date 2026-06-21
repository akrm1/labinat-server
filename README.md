# Labinat

Labinat is a framework for building applications **declaratively**. You describe what your app is made of — tables, screens, routes, themes — and Labinat validates that description and generates the corresponding source code.

## The problem

Every new project brings the same repeated decisions: how to lay out files, which commands to run, how to generate code from a data model. These decisions are rarely written down in a machine-readable way, which means they get re-made on every project — and AI agents working alongside developers have no reliable contract to work from.

## How Labinat helps

- **One shared contract.** App structure is described in plain JSON. Humans, scripts, and AI agents all read and write the same format.
- **Reusable stack profiles.** A *factory* bundles everything a stack needs — code templates, build commands, component schemas — into a versioned, shareable unit.
- **Declare once, generate anywhere.** Write a *block* (a short JSON description of one component) and the factory turns it into real source files.
- **Consistent across projects.** Pin a factory version and every project using it gets the same structure, the same commands, the same output.

## Two roles

| Role | What they do |
|------|-------------|
| **Factory author** | Builds and maintains the stack profile — defines component types, code templates, and build/run commands. |
| **App author** | Creates projects and writes blocks — describes the app's components without touching the underlying stack. |

## Status

The core model, validation, and data persistence are complete. Code generation from blocks is under active development.

→ [Technical reference](docs/Concepts.md)

## License

MIT © 2026 Abdulkarim Alanazi — see [LICENSE](LICENSE).
