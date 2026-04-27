---
name: events-patterns
description: Event tracking, activity feeds, webhook delivery, and audit trail patterns for Rails. Reference material for event-driven domain modeling.
user-invocable: false
---

# Events Patterns

## Philosophy: Events as Domain Records, Not Generic Tracking

- Events are rich domain models (CardMoved, CommentAdded, MemberInvited) not generic Event rows
- Activity feeds use polymorphic associations to actual domain records
- Webhooks are simple: Event model → WebhookDelivery model → background job
- State as records: TrackingEvent with type, not tracking_started_at boolean
- Sidekiq for webhook delivery and event processing (Redis-backed)

**vs. Traditional Approach:**
```ruby
# ❌ Generic event blob
Event.create(event_type: "card.moved", data: { card_id: 1, from: 2, to: 3 })

# ❌ Tracking as booleans — tracking_started_at, viewed_at, clicked_at

# ❌ External event bus
EventBus.publish("card.moved", card_id: @card.id)
```

**Good Way:**
```ruby
# ✅ Domain event records with typed models
class CardMoved < ApplicationRecord
  belongs_to :card
  belongs_to :from_column, class_name: "Column"
  belongs_to :to_column, class_name: "Column"
  belongs_to :creator
  belongs_to :account

  after_create_commit :create_activity
  after_create_commit :broadcast_update_later
  after_create_commit :deliver_webhooks_later
end

# ✅ State as records
class TrackingEvent < ApplicationRecord
  belongs_to :trackable, polymorphic: true
  belongs_to :account
  enum :event_kind, { page_view: 0, link_click: 1, form_submit: 2 }
end

# ✅ Activity as polymorphic records
class Activity < ApplicationRecord
  belongs_to :subject, polymorphic: true # CardMoved, CommentAdded, etc.
  belongs_to :account
  belongs_to :creator, optional: true
  scope :recent, -> { order(created_at: :desc).limit(50) }
end
```

## Pattern Index

### Pattern 1: Domain Event Records

Create rich domain models for business events, not generic event tables. Each event type (CardMoved, CommentAdded, MemberInvited, ProjectArchived) gets its own model with typed associations, callbacks for creating activities and delivering webhooks, and a `description` method. Controllers create event records alongside the domain action.

### Pattern 2: Activity Feed with Polymorphic Associations

Build activity feeds that reference actual domain event records via `belongs_to :subject, polymorphic: true`. The Activity model provides scopes for filtering by board/project/account, icon mapping by subject type, and description delegation. Uses Turbo Streams for real-time feed updates. Includes migration with composite indexes on `[account_id, created_at]` and `[board_id, created_at]`.

### Pattern 3: Webhook System

Simple webhook delivery pipeline: WebhookEndpoint model stores URL, subscribed event types (JSON array), and HMAC secret. WebhookDelivery model tracks delivery status (pending/delivered/failed/retrying) with response codes and error messages. Delivery includes HMAC-SHA256 signature headers. Background jobs handle delivery with `retry_on` and a periodic retry job for failed deliveries within 24 hours.

### Pattern 4: Client-Side Event Tracking

Stimulus controller captures user interactions (page views, link clicks, button clicks, form submissions) and POSTs to a TrackingEvent endpoint. TrackingEvent model uses enum event types, polymorphic `trackable` association, and JSONB metadata for flexible attributes. Views attach tracking behavior via Stimulus data attributes.

### Pattern 5: Event Sourcing for Audit Trails

Immutable event records (e.g., CardUpdated) store serialized `changes` hash (attribute → [old, new]) for compliance audit trails. Models use `after_update` callbacks to automatically record `saved_changes`. Audit views show attribute-level diffs with old/new values and updater attribution.

### Pattern 6: Event Aggregation and Reporting

EventSummary PORO aggregates counts across event types for configurable date ranges. Methods for card_moves, comments_added, members_invited, most_active_boards (top 5), most_active_users (top 10), and daily_activity breakdown. Controller wires date range params to summary object for dashboard views.

## Common Patterns

### Event-Driven Architecture
```ruby
after_create_commit :publish_created_event

def publish_created_event
  CardCreated.create!(card: self, creator: Current.user, account: account)
end

# Events trigger side effects: activities, webhooks, notifications
```

### Polymorphic Event Subjects
```ruby
belongs_to :subject, polymorphic: true    # Activity → any event type
belongs_to :event, polymorphic: true      # WebhookDelivery → any event type
belongs_to :trackable, polymorphic: true  # TrackingEvent → any model
```

### Event Metadata as JSONB
```ruby
t.jsonb :metadata, default: {}
TrackingEvent.where("metadata->>'format' = ?", "csv")
```

### Background Processing
```ruby
after_create_commit :deliver_webhooks_later

def deliver_webhooks_later
  WebhookDeliveryJob.perform_later("card.moved", self)
end
```

## Performance Tips

1. **Eager Load Polymorphic Associations:** `Activity.includes(:subject, :creator).recent`
2. **Index Event Queries:** `add_index :activities, [:account_id, :created_at]`
3. **Batch Webhook Deliveries:** Use background jobs, never deliver synchronously
4. **Limit Activity Feed Results:** `scope :recent, -> { order(created_at: :desc).limit(50) }`
5. **Use Background Jobs for Heavy Processing:** `after_create_commit :process_event_later`

## Testing Patterns

Test event creation and activity feed generation, webhook delivery success/failure/retry, payload construction and HMAC signatures, cross-account isolation, and real-time activity feed updates via system tests. See reference file for complete test examples covering:

- `CardMovedTest` — activity creation, broadcasts, webhook job enqueuing
- `ActivityTest` — scopes, icon mapping, description delegation
- `WebhookDeliveryTest` — HTTP delivery, failure handling, payload/headers
- `WebhookDeliveryJobTest` — endpoint matching, inactive endpoint skipping
- `ActivitiesTest` (system) — real-time feed updates across sessions

## Additional Resources

- [Detailed Patterns & Code Examples](reference/patterns.md) — Full implementation code for all 6 patterns including models, migrations, controllers, views, Stimulus controllers, and complete test suites

## Agent Verification

- Run focused model/job tests for event creation, activity records, webhook delivery, and retry behavior.
- Run a system or integration test for user-visible activity feeds or real-time updates.
- Verify account scoping on event queries and webhook endpoints.
