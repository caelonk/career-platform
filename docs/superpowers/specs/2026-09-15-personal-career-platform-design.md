# Personal Career Platform Design Specification

**Status:** Approved design, pending implementation planning  
**Date:** 2026-09-15

## 1. Purpose and goals

The product is a database-driven personal resume and career platform for a professional pursuing business transformation, digital transformation, IT strategy, and consulting roles. Its first audience is recruiters and hiring managers.

The first release must present a polished, recruiter-friendly personal profile while establishing a durable content model for future career-platform capabilities. Content must be editable through an authenticated administrative experience rather than being hardcoded into page components.

The platform will grow in phases:

1. Public resume, profile, portfolio, and basic content administration.
2. Rich case studies, insights publishing, and opportunity/application tracking.
3. Broader career workflows such as contacts, networking activity, tasks, and related platform modules.

The first release should not attempt to expose every future workflow publicly or build a multi-user social network. It should create clean boundaries that allow those capabilities to be added without replacing the public-content foundation.

## 2. Visitor experience

### Public home page

The public home page uses a hybrid structure:

1. **Executive profile:** name, professional headline, value proposition, target role themes, and primary contact or resume CTA.
2. **Selected resume content:** concise experience highlights, capabilities, certifications, and measurable achievements.
3. **Featured transformation case studies:** a small set of published projects with clear business context, responsibilities, approach, and outcomes.
4. **Contact and next step:** a low-friction contact path and links to downloadable or printable resume material where available.

The presentation should optimize for quick recruiter scanning while allowing deeper reading. Public pages must use semantic, accessible content and stable URLs suitable for sharing and search indexing.

### Public content visibility

Every public-facing content record must have an explicit publication state. Only records marked published and meeting any publication date rules may appear on public pages.

Incomplete resume content remains hidden until it is ready for publication. Major future modules may be visible as clearly labeled roadmap placeholders, using specific labels such as:

- "Case studies in progress"
- "Career tools coming soon"
- "Insights coming soon"

Placeholders must not imply that unavailable functionality is usable. They should be visually distinct from published content and must not expose internal notes, draft text, or private data.

## 3. Scope

### Initial release

- Public profile and landing page
- Resume-oriented experience, skills, certifications, and achievements
- Published project and case-study pages
- Organization and role relationships
- Media and external-link references for case studies
- Authenticated admin interface for creating, editing, previewing, publishing, and unpublishing content
- Public snapshot generation and serving fallback
- Database migrations, backup policy, and recovery verification

### Planned later modules

The data model should leave room for, but the initial release does not need to fully implement:

- Insights/articles and taxonomy
- Job opportunities and application tracking
- Saved roles and application stages
- Professional contacts and networking activity
- Tasks, reminders, and activity history
- Additional public or private career tools

These modules must remain isolated from the initial public-content flows so that adding them does not change the public site's publication rules.

## 4. Proposed architecture

The application will use a full-stack server-side architecture:

- A server-rendered or server-loaded public web application provides public pages.
- Server-side loaders/actions or equivalent request handlers read and mutate data.
- A typed ORM or typed database access layer owns query and persistence boundaries.
- PostgreSQL is accessed only from trusted server code.
- Database credentials are stored in server-side environment configuration and are never bundled into browser code.
- The browser communicates with application routes/actions, not directly with PostgreSQL.

The architecture should separate:

1. **Presentation:** public pages, admin pages, forms, previews, and error states.
2. **Application services:** publication rules, snapshot generation, project reads, and administrative mutations.
3. **Data access:** typed repositories/query functions and transaction boundaries.
4. **Persistence:** PostgreSQL schema, migrations, indexes, constraints, and backups.
5. **Snapshot delivery:** generation and serving of the last known-good public representation.

Public project reads should use a dedicated published-content query path rather than returning arbitrary database records. Admin reads may include drafts and private metadata only after authentication and authorization checks.

## 5. Data model

PostgreSQL is the system of record because the platform needs relational integrity, constraints, flexible queries, and clear relationships as the feature set grows.

### Core entities

The initial schema should support these entities:

- **Profile:** the primary public identity, headline, summary, value proposition, contact details, and site-level settings.
- **Experience:** employment or engagement history, organization, role title, dates, summary, responsibilities, achievements, and visibility.
- **Organization:** employers, clients, partners, or other relevant organizations.
- **Role:** reusable role or capability framing associated with experience, projects, or target positioning.
- **Project:** a portfolio item or transformation initiative with title, slug, summary, context, problem, responsibilities, approach, outcomes, metrics, dates, organization, role, and publication state.
- **Skill:** reusable skills grouped by category, with ordering and visibility.
- **Certification:** certification name, issuer, date information, credential URL/reference, and visibility.
- **Achievement:** reusable measurable accomplishment or highlight associated with experience or projects.
- **Media asset:** image, document, or external media metadata referenced by projects or profile content; binary storage may be external to PostgreSQL.
- **External link:** labeled URL references for projects, profile, organizations, or supporting evidence.
- **Publication metadata:** draft/published state, slug, publication timestamps, author/editor timestamps, and optional scheduled publication behavior.

Many-to-many relationships should be modeled explicitly where reuse matters, especially Project-Skill, Project-Achievement, Experience-Skill, and Project-Media. Foreign keys, uniqueness constraints for slugs and stable identifiers, and check constraints for valid publication/date states should prevent invalid content.

### Future entities

The schema may later add:

- Insight/article and taxonomy records
- Opportunity, application, and application-stage records
- Contact, organization-contact relationship, and networking activity records
- Task and reminder records
- Audit/activity records

Future private career records must have explicit ownership and visibility fields and must never be included by public queries merely because they share an organization or project relationship.

### Project content requirements

A project must be able to represent:

- Title, slug, short summary, and featured status
- Business or organizational context
- Problem or opportunity
- Personal responsibilities and role
- Approach, decisions, and implementation narrative
- Outcomes and measurable metrics
- Related organization, role, skills, achievements, media, and links
- Start/end dates or an equivalent period
- Draft, published, archived, and optionally scheduled publication state

Project content should support structured fields for recruiter scanning while allowing longer narrative sections for detailed case-study pages. Metrics should retain a label and value, with optional context, rather than being stored only as unstructured prose.

## 6. Availability, snapshots, and recovery

### Database outage behavior

The public site must serve the last successfully generated public snapshot when live database reads are unavailable. The snapshot must include the profile identity, headline, value proposition, contact or resume CTA, and core resume content so the profile remains visible and useful during an outage. It should also cover published project pages and public navigation metadata.

Snapshot generation must be tied to a known-good publication state. A failed or incomplete generation must not replace the currently served snapshot. The profile portion of the snapshot must be independently addressable or otherwise guaranteed to render even if a project or secondary public section cannot be generated. The system should expose an operational status signal for administrators without displaying internal failure details to visitors.

Admin editing and publishing require live database access. If the database is unavailable, the admin experience should fail explicitly with a useful retry message rather than reporting a false save.

### Recovery verification

Recovery procedures must include:

- Automated backup restore into an isolated verification environment
- Migration/schema validation against the restored database
- Connectivity and authentication checks
- Representative published project reads
- Public page end-to-end checks using restored data
- Authenticated admin edit, preview, publish, and read-back checks
- Verification that snapshot generation succeeds after restore

The recovery test must report failures and must not silently treat a partial restore as successful. Backup retention, recovery point objectives, and recovery time objectives should be selected during implementation planning based on the hosting provider and risk tolerance; the test harness must record the observed restore and validation duration.

## 7. Error handling and security

- Public database read failures fall back to the last known-good snapshot and emit server-side operational telemetry.
- Snapshot generation failures preserve the previous snapshot and surface an administrative error.
- Admin validation errors are returned per field and do not persist partial invalid records.
- Database constraint or transaction failures are surfaced as an unsuccessful operation; they must not be converted into success-shaped responses.
- Authentication and authorization are mandatory for all draft, private, and mutation routes.
- Public queries must enforce publication and visibility rules at the data-access boundary.
- Secrets, database URLs, private contact data, and internal notes must never be serialized into public payloads or client bundles.
- Uploaded or linked media must be validated and served through an approved storage path.
- Auditability should be available for publication and administrative mutations before private career workflows are added.

## 8. Testing and acceptance criteria

The implementation is acceptable when:

- A visitor can reach a hybrid profile/resume home page without authentication.
- Published projects render their structured case-study content and related metadata.
- Draft and private projects are absent from public pages, navigation, search, and snapshot output.
- Major planned modules can display labeled placeholders without exposing unfinished resume content.
- An administrator can create, edit, preview, publish, unpublish, and update a project through server-side actions.
- No browser code requires or receives direct PostgreSQL credentials.
- The profile, headline, value proposition, contact or resume CTA, and core resume content remain visible from the last good snapshot during a simulated database outage.
- Published project pages and public navigation remain available from the last good snapshot when they were included in that snapshot.
- A failed snapshot generation leaves the previous snapshot intact.
- Automated restore verification can restore a backup and prove database reads, public rendering, admin editing, and snapshot generation.
- Relationship constraints and publication-state rules prevent orphaned or accidentally public records.

Testing should include unit tests for publication and visibility rules, integration tests for repositories and transactions, and end-to-end tests for public browsing, admin editing, snapshot fallback, and restore verification.

## 9. Delivery boundaries

Implementation should proceed in independently testable slices:

1. Persistence foundation and migrations
2. Public profile/resume content and published project reads
3. Admin project/content editing and publication workflow
4. Snapshot generation and outage fallback
5. Backup/restore verification and operational checks

Opportunity tracking, networking, tasks, and other career-platform modules are intentionally deferred until the public-content foundation is stable. Their future schemas and routes should not compromise the initial public visitor experience or introduce direct browser-to-database access.

## 10. Decisions and assumptions

- The primary audience is recruiters and hiring managers.
- The target positioning is business transformation, digital transformation, IT strategy, and consulting, specifically avoiding an IT help desk framing.
- PostgreSQL is the selected database engine.
- Full case-study content is required, including problem, context, responsibilities, approach, outcomes, metrics, media, and related skills.
- The public fallback is the last successfully generated full-site snapshot.
- Recovery verification includes automated backup restore plus end-to-end public and admin checks.
- The application uses server-side loaders/actions and a typed ORM; the browser never connects directly to PostgreSQL.
- Public placeholders are permitted for major roadmap modules, while incomplete resume content remains hidden.
