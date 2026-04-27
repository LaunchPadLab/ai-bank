---
name: "sidekiq-setup"
description: "Configures Sidekiq for background jobs in Rails 8. Use when setting up background processing, creating background jobs, configuring job queues, or when user mentions Sidekiq, background jobs, or Redis-backed queues."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools, argument-hint. -->

# Sidekiq Setup for Rails 8

**Job to create: $ARGUMENTS**

## Overview

Sidekiq is a high-performance background job processor for Ruby:
- Redis-backed for speed and reliability
- Thread-based concurrency (handles many jobs per process)
- Built-in retry with exponential backoff
- Web UI dashboard for monitoring
- Supports scheduled jobs, batches, and rate limiting

## Assumptions

Use this skill only when the project has chosen Sidekiq or the user explicitly asks for Sidekiq. Rails 8 greenfield apps may use Solid Queue by default; if the repo already uses Solid Queue and the user did not request Sidekiq, keep the existing queue backend.

## Quick Start

### Installation

```bash
# Add to Gemfile
bundle add sidekiq

# Start Redis (required)
brew install redis && brew services start redis
```

### Configuration

```yaml
# config/sidekiq.yml
:concurrency: 5
:queues:
  - [critical, 3]
  - [default, 2]
  - [low, 1]

production:
  :concurrency: 10
  :queues:
    - [critical, 5]
    - [default, 3]
    - [low, 1]
```

### Set as Active Job Adapter

```ruby
# config/application.rb
config.active_job.queue_adapter = :sidekiq
```

### Mount Web UI

```ruby
# config/routes.rb
require "sidekiq/web"

Rails.application.routes.draw do
  mount Sidekiq::Web => "/sidekiq"
end
```

## Workflow Checklist

```
Sidekiq Setup:
- [ ] Add sidekiq gem
- [ ] Install and start Redis
- [ ] Configure config/sidekiq.yml
- [ ] Set queue adapter in config/application.rb
- [ ] Mount Sidekiq::Web in routes
- [ ] Create first job
- [ ] Test job execution
- [ ] Configure scheduled jobs (if needed)
```

## Creating Jobs

### Native Sidekiq Job (Preferred)

```ruby
# app/jobs/send_welcome_email_job.rb
class SendWelcomeEmailJob
  include Sidekiq::Job
  sidekiq_options queue: :default, retry: 5

  def perform(user_id)
    user = User.find(user_id)
    UserMailer.welcome(user).deliver_now
  end
end
```

### ActiveJob (Alternative)

```ruby
# app/jobs/send_welcome_email_job.rb
class SendWelcomeEmailJob < ApplicationJob
  queue_as :default

  def perform(user_id)
    user = User.find(user_id)
    UserMailer.welcome(user).deliver_now
  end
end
```

### Job with Retry and Error Handling

```ruby
class ProcessPaymentJob
  include Sidekiq::Job
  sidekiq_options queue: :critical, retry: 5, backtrace: true

  sidekiq_retries_exhausted do |job, exception|
    ErrorNotifier.notify(exception, context: job)
  end

  def perform(order_id)
    order = Order.find(order_id)
    PaymentService.new.charge(order)
  end
end
```

## Enqueueing Jobs

```ruby
# Native Sidekiq (preferred)
SendWelcomeEmailJob.perform_async(user.id)
SendReminderJob.perform_in(1.hour, user.id)
SendReportJob.perform_at(Date.tomorrow.noon, report.id)

# Bulk enqueue (single Redis round trip)
args = users.map { |u| [u.id] }
SendWelcomeEmailJob.perform_bulk(args)

# ActiveJob style (also works)
SendWelcomeEmailJob.perform_later(user.id)
SendReminderJob.set(wait: 1.hour).perform_later(user.id)
```

## Scheduled/Recurring Jobs

Use `sidekiq-cron` or `sidekiq-scheduler` gem:

```ruby
# Gemfile
gem "sidekiq-cron"
```

```ruby
# config/initializers/sidekiq_cron.rb
Sidekiq::Cron::Job.create(
  name: "Daily Report",
  cron: "0 6 * * *",
  class: "GenerateDailyReportJob"
)

Sidekiq::Cron::Job.create(
  name: "Cleanup Old Records",
  cron: "0 2 * * 0",
  class: "CleanupOldRecordsJob"
)
```

## Testing Jobs

### Native Sidekiq Jobs

Use Sidekiq's test helpers for classes that include `Sidekiq::Job` and enqueue with `perform_async`.

```ruby
# test/jobs/send_welcome_email_job_test.rb
require "test_helper"
require "sidekiq/testing"

class SendWelcomeEmailJobTest < ActiveSupport::TestCase
  setup do
    Sidekiq::Testing.fake!
    SendWelcomeEmailJob.clear
  end

  test "enqueues the job" do
    user = users(:one)

    assert_difference -> { SendWelcomeEmailJob.jobs.size }, 1 do
      SendWelcomeEmailJob.perform_async(user.id)
    end
  end

  test "sends welcome email when performed" do
    user = users(:one)

    assert_emails 1 do
      SendWelcomeEmailJob.perform_async(user.id)
      SendWelcomeEmailJob.drain
    end
  end
end
```

### Active Job Wrapper

Use Active Job assertions only for jobs that inherit from `ApplicationJob` and enqueue with `perform_later`.

```ruby
class WelcomeEmailJob < ApplicationJob
  queue_as :default

  def perform(user)
    UserMailer.welcome(user).deliver_later
  end
end

class WelcomeEmailJobTest < ActiveJob::TestCase
  include ActiveJob::TestHelper

  test "enqueues welcome email" do
    user = users(:one)

    assert_enqueued_email_with UserMailer, :welcome, args: [user] do
      WelcomeEmailJob.perform_later(user)
    end
  end
end
```

### Sidekiq Testing Modes

```ruby
# test/test_helper.rb
require "sidekiq/testing"
Sidekiq::Testing.fake!  # Jobs are pushed to a per-class array (default for tests)

# In tests:
test "enqueues job" do
  assert_equal 0, SendWelcomeEmailJob.jobs.size
  SendWelcomeEmailJob.perform_async(1)
  assert_equal 1, SendWelcomeEmailJob.jobs.size
end

# Inline mode (execute immediately)
Sidekiq::Testing.inline! do
  SendWelcomeEmailJob.perform_async(1)  # runs synchronously
end
```

## Running Sidekiq

```bash
# Development
bundle exec sidekiq

# With specific config
bundle exec sidekiq -C config/sidekiq.yml

# Production (via Procfile)
# Procfile
web: bin/rails server
worker: bundle exec sidekiq -C config/sidekiq.yml
```

## Monitoring

### Web UI

```ruby
# Access at /sidekiq after mounting in routes
# Shows queues, retries, scheduled jobs, dead jobs, and stats
```

### Console Queries

```ruby
# Queue sizes
Sidekiq::Queue.new("default").size
Sidekiq::Queue.new("critical").size

# Retry set
Sidekiq::RetrySet.new.size

# Dead jobs
Sidekiq::DeadSet.new.size

# Clear retry queue
Sidekiq::RetrySet.new.clear

# Stats
stats = Sidekiq::Stats.new
stats.processed
stats.failed
stats.enqueued
```

## Key Differences from Solid Queue

| Solid Queue | Sidekiq |
|-------------|---------|
| `perform_later(args)` | `perform_async(args)` |
| `set(wait: 5.minutes).perform_later(args)` | `perform_in(5.minutes, args)` |
| `queue_as :critical` | `sidekiq_options queue: :critical` |
| `retry_on` with `wait:` | `sidekiq_options retry: N` |
| Database-backed | Redis-backed |
| `solid_queue:start` | `bundle exec sidekiq` |

## Reference

- [Domain Patterns](reference/domain-patterns.md) — 7 job patterns, retry strategies, recurring jobs, error handling, batch processing, testing, monitoring
