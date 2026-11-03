# Decisions and Rationale

The team decided to keep the first release server-rendered instead of building a separate JavaScript client. This keeps volunteer maintenance simple and avoids adding a second deployment pipeline.

The registration page switched to a weekly cache in October. The notes say the cache reduced repeated database reads, but the original decision rationale is missing. Confirm the invalidation behavior before changing the schedule.
