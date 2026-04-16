# Sidekiq Job Domain Patterns

Recovered from jobs-agent.md — comprehensive job patterns for Rails 8 with Sidekiq, including native API usage, retry strategies, and testing.

## Core Philosophy

**Jobs should be simple, reliable, and observable.** Sidekiq provides battle-tested background processing backed by Redis.

### Why Sidekiq:
- Battle-tested at scale (billions of jobs processed)
- Redis-backed for high throughput and low latency
- Rich ecosystem (sidekiq-cron, sidekiq-unique-jobs, Sidekiq Pro/Enterprise)
- Built-in web dashboard for monitoring and debugging
- Reliable retry with exponential backoff out of the box
- Concurrency via threads (efficient memory usage)

### Why native Sidekiq over ActiveJob:
- Direct access to Sidekiq features (`sidekiq_options`, `perform_in`, batches)
- Better performance (no ActiveJob serialization overhead)
- Native retry configuration per job class
- `perform_async` / `perform_in` / `perform_at` for flexible scheduling
- Use ActiveJob wrapper only when you need adapter portability

---

## Job Patterns

### Pattern 1: Native Sidekiq job (preferred for performance)

```ruby
# app/sidekiq/notify_recipients_worker.rb
class NotifyRecipientsWorker
  include Sidekiq::Job

  sidekiq_options queue: "default", retry: 5

  def perform(notifiable_type, notifiable_id)
    notifiable = notifiable_type.constantize.find(notifiable_id)
    notifiable.notify_recipients
  end
end
```

```ruby
NotifyRecipientsWorker.perform_async("Comment", comment.id)
NotifyRecipientsWorker.perform_in(5.minutes, "Comment", comment.id)
NotifyRecipientsWorker.perform_at(1.hour.from_now, "Comment", comment.id)
```

### Pattern 2: ActiveJob with Sidekiq adapter

```ruby
# app/jobs/notify_recipients_job.rb
class NotifyRecipientsJob < ApplicationJob
  queue_as :default

  def perform(notifiable)
    notifiable.notify_recipients
  end
end
```

```ruby
# app/models/concerns/notifiable.rb
module Notifiable
  extend ActiveSupport::Concern

  def notify_recipients_async
    NotifyRecipientsJob.perform_later(self)
  end

  def notify_recipients
    recipients.each do |recipient|
      next if recipient == creator

      Notification.create!(
        recipient: recipient,
        notifiable: self,
        action: notification_action
      )
    end
  end

  private

  def recipients
    []
  end

  def notification_action
    "#{self.class.name.underscore}_created"
  end
end
```

```ruby
class Comment < ApplicationRecord
  include Notifiable

  after_create_commit :notify_recipients_async

  private

  def recipients
    card.watchers + card.assignees + [card.creator]
  end
end
```

### Pattern 3: Batch processing job

```ruby
# app/sidekiq/deliver_bundled_notifications_worker.rb
class DeliverBundledNotificationsWorker
  include Sidekiq::Job

  sidekiq_options queue: "default", retry: 3

  def perform
    Notification::Bundle.deliver_all
  end
end
```

```ruby
# app/models/notification/bundle.rb
class Notification::Bundle
  def self.deliver_all
    User.find_each do |user|
      bundle = new(user)
      bundle.deliver if bundle.has_notifications?
    end
  end

  attr_reader :user

  def initialize(user)
    @user = user
  end

  def has_notifications?
    unread_notifications.any?
  end

  def deliver
    NotificationMailer.bundled(user, unread_notifications).deliver_now
    mark_as_bundled
  end

  private

  def unread_notifications
    @unread_notifications ||= user.notifications.unread.where("created_at > ?", 30.minutes.ago)
  end

  def mark_as_bundled
    unread_notifications.update_all(bundled_at: Time.current)
  end
end
```

### Pattern 4: Cleanup job

```ruby
# app/sidekiq/session_cleanup_worker.rb
class SessionCleanupWorker
  include Sidekiq::Job

  sidekiq_options queue: "low_priority", retry: 1

  def perform
    Session.where("created_at < ?", 30.days.ago).delete_all
    MagicLink.where("expires_at < ?", 1.day.ago).delete_all
  end
end
```

### Pattern 5: Event tracking job

```ruby
# app/sidekiq/track_event_worker.rb
class TrackEventWorker
  include Sidekiq::Job

  sidekiq_options queue: "default", retry: 3

  def perform(eventable_type, eventable_id, action, options = {})
    eventable = eventable_type.constantize.find(eventable_id)

    eventable.events.create!(
      account: eventable.account,
      action: action,
      user_id: options["user_id"],
      particulars: options["particulars"] || {}
    )
  end
end
```

```ruby
TrackEventWorker.perform_async(
  "Card", @card.id, "card_closed",
  { "user_id" => Current.user.id, "particulars" => { "reason" => "Completed" } }
)
```

### Pattern 6: External API job with retries

```ruby
# app/sidekiq/dispatch_webhook_worker.rb
class DispatchWebhookWorker
  include Sidekiq::Job

  sidekiq_options queue: "webhooks", retry: 5, dead: true

  sidekiq_retry_in do |count, _exception|
    (count ** 4) + 15 + (rand(10) * (count + 1))
  end

  def perform(webhook_id, event_data)
    webhook = Webhook.find(webhook_id)
    response = HTTP.post(webhook.url, json: event_data)

    if response.status.success?
      webhook.increment!(:successful_deliveries)
    else
      webhook.increment!(:failed_deliveries)
      raise "Webhook delivery failed: #{response.status}"
    end
  end
end
```

### Pattern 7: Broadcasting job (ActiveJob)

```ruby
# app/jobs/broadcast_update_job.rb
class BroadcastUpdateJob < ApplicationJob
  queue_as :default

  def perform(broadcastable)
    broadcastable.broadcast_update
  end
end
```

```ruby
# app/models/concerns/broadcastable.rb
module Broadcastable
  extend ActiveSupport::Concern

  included do
    after_update_commit :broadcast_update_async
  end

  def broadcast_update_async
    BroadcastUpdateJob.perform_later(self)
  end

  def broadcast_update
    broadcast_replace_to board,
      target: self,
      partial: partial_path,
      locals: { self.model_name.element.to_sym => self }
  end

  private

  def partial_path
    "#{self.class.name.underscore.pluralize}/#{self.class.name.underscore}"
  end
end
```

---

## Recurring Jobs with sidekiq-cron

### Configuration

```ruby
# config/initializers/sidekiq_cron.rb
Sidekiq::Cron::Job.load_from_hash(
  "deliver_bundled_notifications" => {
    "class" => "DeliverBundledNotificationsWorker",
    "cron" => "*/30 * * * *",
    "queue" => "default",
    "description" => "Bundle and send notifications every 30 minutes"
  },
  "cleanup_old_sessions" => {
    "class" => "SessionCleanupWorker",
    "cron" => "0 3 * * *",
    "queue" => "low_priority",
    "description" => "Cleanup old sessions daily at 3am"
  },
  "mark_entropic_cards" => {
    "class" => "MarkEntropicCardsWorker",
    "cron" => "0 2 * * *",
    "queue" => "default",
    "description" => "Mark entropic cards daily at 2am"
  },
  "weekly_digest" => {
    "class" => "WeeklyDigestWorker",
    "cron" => "0 9 * * 0",
    "queue" => "default",
    "description" => "Send weekly digest on Sundays at 9am"
  }
)
```

### Recurring worker example

```ruby
# app/sidekiq/mark_entropic_cards_worker.rb
class MarkEntropicCardsWorker
  include Sidekiq::Job

  sidekiq_options queue: "default", retry: 1

  def perform
    Card.entropic.find_each do |card|
      card.postpone(user: nil)
    end
  end
end
```

```ruby
class Card < ApplicationRecord
  scope :entropic, -> {
    open
      .published
      .where.missing(:not_now)
      .where("updated_at < ?", 30.days.ago)
  }
end
```

---

## Sidekiq Configuration

### sidekiq.yml

```yaml
# config/sidekiq.yml
:concurrency: 10
:timeout: 25

:queues:
  - [default, 5]
  - [webhooks, 3]
  - [low_priority, 1]

production:
  :concurrency: 25

staging:
  :concurrency: 10
```

### Rails configuration

```ruby
# config/environments/production.rb
config.active_job.queue_adapter = :sidekiq
```

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  config.redis = { url: ENV.fetch("REDIS_URL", "redis://localhost:6379/0") }
end

Sidekiq.configure_client do |config|
  config.redis = { url: ENV.fetch("REDIS_URL", "redis://localhost:6379/0") }
end
```

### Web dashboard

```ruby
# config/routes.rb
require "sidekiq/web"

Rails.application.routes.draw do
  authenticate :user, ->(user) { user.admin? } do
    mount Sidekiq::Web => "/sidekiq"
  end
end
```

---

## Retry Strategies

### Per-job retry configuration

```ruby
class DispatchWebhookWorker
  include Sidekiq::Job

  sidekiq_options retry: 5

  sidekiq_retry_in do |count, _exception|
    (count ** 4) + 15 + (rand(10) * (count + 1))
  end

  def perform(webhook_id, event_data)
    # ...
  end
end
```

### ActiveJob retry (when using ActiveJob wrapper)

```ruby
class ImportDataJob < ApplicationJob
  retry_on CustomError, wait: 5.minutes, attempts: 3
  discard_on ActiveRecord::RecordNotFound

  def perform(import)
    import.process
  end
end
```

### Dead job handling

```ruby
class ProcessPaymentWorker
  include Sidekiq::Job

  sidekiq_options retry: 5, dead: true

  sidekiq_retries_exhausted do |msg, _exception|
    ExceptionTracker.notify(
      "Payment processing failed permanently",
      job_id: msg["jid"],
      args: msg["args"]
    )
  end

  def perform(payment_id)
    Payment.find(payment_id).process
  end
end
```

---

## Job Argument Serialization

### Native Sidekiq (primitives only)

```ruby
NotifyRecipientsWorker.perform_async("Comment", 123)
SendEmailWorker.perform_async("user@example.com", "Subject")
ProcessDataWorker.perform_async(1, "string", true, [1, 2, 3], { "key" => "value" })
```

### ActiveJob (GlobalID serialization)

```ruby
NotifyRecipientsJob.perform_later(@comment)
# Serialized as: { "_aj_globalid" => "gid://app/Comment/123" }
```

### Complex arguments

```ruby
class TrackEventWorker
  include Sidekiq::Job

  def perform(eventable_type, eventable_id, action, options = {})
    eventable = eventable_type.constantize.find(eventable_id)
    user = User.find(options["user_id"]) if options["user_id"]
    particulars = options["particulars"] || {}

    eventable.events.create!(
      account: eventable.account,
      action: action,
      user: user,
      particulars: particulars
    )
  end
end

TrackEventWorker.perform_async(
  "Card", @card.id, "card_closed",
  { "user_id" => @user.id, "particulars" => { "reason" => "Completed" } }
)
```

---

## Error Handling

### Log errors

```ruby
class ProcessImportWorker
  include Sidekiq::Job

  sidekiq_options retry: 3

  def perform(import_id)
    import = Import.find(import_id)
    import.process
  rescue StandardError => exception
    Rails.logger.error "Import failed: #{exception.message}"
    Rails.logger.error exception.backtrace.join("\n")
    ExceptionTracker.notify(exception, job: self.class.name, import_id: import_id)
    raise
  end
end
```

### Handle specific errors

```ruby
class DispatchWebhookWorker
  include Sidekiq::Job

  sidekiq_options retry: 5

  sidekiq_retries_exhausted do |msg, exception|
    webhook = Webhook.find(msg["args"].first)
    webhook.disable!
    ExceptionTracker.notify(exception, webhook_id: webhook.id)
  end

  def perform(webhook_id, event_data)
    webhook = Webhook.find(webhook_id)
    webhook.dispatch(event_data)
  end
end
```

---

## Job Lifecycle Callbacks

```ruby
class ComplexWorker
  include Sidekiq::Job

  def perform(record_type, record_id)
    record = record_type.constantize.find(record_id)
    Current.user = record.creator if record.respond_to?(:creator)

    start_time = Time.current
    record.process
    duration = Time.current - start_time

    Rails.logger.info "Job completed in #{duration}s"
  ensure
    Current.reset
  end
end
```

---

## Performance Patterns

### Batch processing

```ruby
class ProcessCardsWorker
  include Sidekiq::Job

  sidekiq_options queue: "default"

  def perform(card_ids)
    Card.where(id: card_ids).find_each do |card|
      card.process
    end
  end
end

Card.active.pluck(:id).each_slice(100) do |batch|
  ProcessCardsWorker.perform_async(batch)
end
```

### Unique jobs (sidekiq-unique-jobs)

```ruby
class ReindexBoardWorker
  include Sidekiq::Job

  sidekiq_options lock: :until_executed, queue: "default"

  def perform(board_id)
    board = Board.find(board_id)
    board.reindex
  end
end
```

---

## Testing Jobs

### Unit tests (Minitest)

```ruby
class CommentTest < ActiveSupport::TestCase
  test "notify_recipients creates notifications" do
    comment = comments(:logo_comment)

    assert_difference -> { Notification.count }, 2 do
      comment.notify_recipients
    end
  end

  test "doesn't notify comment creator" do
    comment = comments(:logo_comment)
    creator_id = comment.creator_id

    comment.notify_recipients

    refute Notification.exists?(recipient_id: creator_id, notifiable: comment)
  end
end
```

### Job tests (verify job is enqueued)

```ruby
require "test_helper"

class NotifyRecipientsJobTest < ActiveJob::TestCase
  test "enqueues job" do
    comment = comments(:logo_comment)

    assert_enqueued_with job: NotifyRecipientsJob, args: [comment] do
      NotifyRecipientsJob.perform_later(comment)
    end
  end

  test "calls notify_recipients" do
    comment = comments(:logo_comment)

    assert_difference -> { Notification.count }, 2 do
      NotifyRecipientsJob.perform_now(comment)
    end
  end
end
```

### Native Sidekiq worker tests

```ruby
require "test_helper"

class NotifyRecipientsWorkerTest < ActiveSupport::TestCase
  test "creates notifications for recipients" do
    comment = comments(:logo_comment)

    assert_difference -> { Notification.count }, 2 do
      NotifyRecipientsWorker.new.perform("Comment", comment.id)
    end
  end
end
```

### Integration tests (verify callbacks enqueue jobs)

```ruby
test "creating comment enqueues notification job" do
  card = cards(:logo)

  assert_enqueued_with job: NotifyRecipientsJob do
    card.comments.create!(body: "Great work!", creator: users(:david))
  end
end
```

### Testing recurring jobs

```ruby
test "marks entropic cards as postponed" do
  card = cards(:old_card)
  card.update!(updated_at: 31.days.ago)

  assert_difference -> { Card::NotNow.count }, 1 do
    MarkEntropicCardsWorker.new.perform
  end

  assert card.reload.postponed?
end
```

---

## Monitoring Jobs

### Sidekiq web dashboard

```ruby
mount Sidekiq::Web => "/sidekiq"

# Dashboard shows:
# - Queue sizes and latency
# - Active/retry/dead job counts
# - Real-time processing stats
# - Job details and retry/kill controls
```

### Performance metrics

```ruby
class ApplicationJob < ActiveJob::Base
  around_perform do |job, block|
    start = Time.current
    block.call
    duration = Time.current - start

    Rails.logger.info "[Job] #{job.class.name} completed in #{duration}s"

    ActiveSupport::Notifications.instrument(
      "job.duration",
      job_class: job.class.name,
      duration: duration
    )
  end
end
```

---

## Common Job Patterns Catalog

| Pattern | Perform Method |
|---------|---------------|
| Notification | `notifiable.notify_recipients` |
| Cleanup | `Model.where("created_at < ?", 30.days.ago).delete_all` |
| Batch processing | `Model.where(id: record_ids).find_each(&:process)` |
| External API | `record.sync_to_external_service` |
| Broadcasting | `broadcastable.broadcast_update` |
| Email (built-in) | `UserMailer.welcome(user).deliver_later` |

---

## Process Management

```bash
# Start Sidekiq
bundle exec sidekiq

# Start with config file
bundle exec sidekiq -C config/sidekiq.yml

# Procfile
web: bundle exec puma -C config/puma.rb
worker: bundle exec sidekiq -C config/sidekiq.yml
```

---

## Boundaries

- **Always do:** Use `sidekiq_options` for queue/retry config, prefer `perform_async` for native jobs, pass only JSON-safe primitives to native workers, set queue priorities, implement retry strategies, test jobs with Minitest, handle errors gracefully, log job performance, use sidekiq-cron for scheduled tasks, monitor via web dashboard
- **Ask first:** Before putting business logic in jobs (consider models/services), before creating custom middleware, before bypassing retry mechanisms, before running jobs synchronously in production
- **Never do:** Pass complex Ruby objects to native workers (use IDs), forget to handle errors, skip retry strategies for unreliable operations, enqueue jobs in transactions (may not commit), forget to test jobs, run expensive operations synchronously, forget `Current.reset` in jobs, skip monitoring job queues, use `perform_async` with ActiveRecord objects in native workers
