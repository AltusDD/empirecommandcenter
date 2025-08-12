# Table `doorloop_raw_owners`

**Primary Key:** `id`

## Columns

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `text` | `NO` | `` |
| `data` | `jsonb` | `YES` | `` |
| `source_endpoint` | `text` | `YES` | `` |
| `inserted_at` | `timestamptz` | `YES` | `now()` |
| `outgoingEPay` | `jsonb` | `YES` | `` |
| `companyName` | `text` | `YES` | `` |
| `firstName` | `text` | `YES` | `` |
| `managementStartDate` | `timestamptz` | `YES` | `` |
| `active` | `bool` | `YES` | `` |
| `createdBy` | `text` | `YES` | `` |
| `createdAt` | `timestamptz` | `YES` | `` |
| `emails` | `jsonb` | `YES` | `` |
| `batch` | `text` | `YES` | `` |
| `fullName` | `text` | `YES` | `` |
| `jobTitle` | `text` | `YES` | `` |
| `updatedAt` | `timestamptz` | `YES` | `` |
| `primaryAddress` | `jsonb` | `YES` | `` |
| `properties` | `jsonb` | `YES` | `` |
| `e164PhoneMobileNumber` | `text` | `YES` | `` |
| `phones` | `jsonb` | `YES` | `` |
| `company` | `bool` | `YES` | `` |
| `alternateAddress` | `jsonb` | `YES` | `` |
| `intercomContactId` | `text` | `YES` | `` |
| `name` | `text` | `YES` | `` |
| `updatedBy` | `text` | `YES` | `` |
| `portalInfo` | `jsonb` | `YES` | `` |
| `conversationWelcomeSmsSentAt` | `timestamptz` | `YES` | `` |
| `lastName` | `text` | `YES` | `` |
| `notes` | `text` | `YES` | `` |

## Indexes

- `doorloop_raw_owners_pkey` — `CREATE UNIQUE INDEX doorloop_raw_owners_pkey ON public.doorloop_raw_owners USING btree (id)`