# Domain Mailer Patterns

Advanced Action Mailer patterns for notification digests, email preferences, multi-tenant emails, and notification persistence.

## Digest / Bundled Notifications

Bundle multiple notifications into a single email to reduce email fatigue.

### DigestMailer

```ruby
# app/mailers/digest_mailer.rb
class DigestMailer < ApplicationMailer
  def daily_activity(user, account, activities)
    @user = user
    @account = account
    @activities = activities
    @grouped_activities = activities.group_by(&:subject_type)

    mail(
      to: user.email,
      subject: "Daily activity summary for #{account.name}",
      from: account_from_address(account)
    )
  end

  def weekly_summary(user, account, summary_data)
    @user = user
    @account = account
    @summary = summary_data

    mail(
      to: user.email,
      subject: "Weekly summary for #{account.name}",
      from: account_from_address(account)
    )
  end

  def pending_notifications(user, notifications)
    @user = user
    @notifications = notifications
    @accounts = notifications.map(&:account).uniq

    mail(
      to: user.email,
      subject: "You have #{notifications.size} pending notifications"
    )
  end
end
```

### NotificationBundler

Decides when to bundle pending notifications into a digest.

```ruby
# app/models/notification_bundler.rb
class NotificationBundler
  THRESHOLD = 5
  MAX_AGE   = 1.hour

  def initialize(user)
    @user = user
  end

  def pending_notifications
    @user.notifications
      .where(sent_at: nil)
      .where("created_at > ?", MAX_AGE.ago)
      .order(created_at: :desc)
  end

  def should_send_digest?
    pending_notifications.count >= THRESHOLD || oldest_pending_notification_age > MAX_AGE
  end

  def send_digest
    return unless should_send_digest?

    notifications = pending_notifications
    DigestMailer.pending_notifications(@user, notifications).deliver_later
    notifications.update_all(sent_at: Time.current)
  end

  private

  def oldest_pending_notification_age
    oldest = pending_notifications.order(created_at: :asc).first
    oldest ? Time.current - oldest.created_at : 0
  end
end
```

### Recurring Digest Job (Sidekiq)

```ruby
# app/sidekiq/send_digest_emails_job.rb
class SendDigestEmailsJob
  include Sidekiq::Job
  sidekiq_options queue: :mailers

  def perform(frequency = "daily")
    User.where(digest_frequency: frequency).find_each do |user|
      user.accounts.each do |account|
        activities = user.activities_for_digest(account, frequency)

        if activities.any?
          DigestMailer.daily_activity(user, account, activities).deliver_now
        end
      end
    end
  end
end
```

Schedule with sidekiq-cron:

```ruby
# config/initializers/sidekiq_cron.rb
Sidekiq::Cron::Job.create(
  name:  "daily_digest",
  cron:  "0 8 * * *",
  class: "SendDigestEmailsJob",
  args:  ["daily"],
  queue: "mailers"
)

Sidekiq::Cron::Job.create(
  name:  "weekly_digest",
  cron:  "0 8 * * 1",
  class: "SendDigestEmailsJob",
  args:  ["weekly"],
  queue: "mailers"
)
```

### Digest Templates

```erb
<%# app/views/digest_mailer/daily_activity.text.erb %>
Hi <%= @user.name %>,

Here's what happened today in <%= @account.name %>:

<% @grouped_activities.each do |type, activities| %>
<%= type.pluralize %> (<%= activities.size %>):
<% activities.first(5).each do |activity| %>
  - <%= activity.description %>
<% end %>
<% if activities.size > 5 %>
  ... and <%= activities.size - 5 %> more
<% end %>

<% end %>

View all activity: <%= account_activities_url(@account) %>

---
You're receiving this because you opted in to daily digests.
Manage preferences: <%= account_settings_url(@account) %>

<%# app/views/digest_mailer/daily_activity.html.erb %>
<p>Hi <%= @user.name %>,</p>

<p>Here's what happened today in <strong><%= @account.name %></strong>:</p>

<% @grouped_activities.each do |type, activities| %>
  <h3 style="font-size: 16px; margin-top: 20px; margin-bottom: 10px;">
    <%= type.pluralize %> (<%= activities.size %>)
  </h3>

  <ul style="margin: 0; padding-left: 20px;">
    <% activities.first(5).each do |activity| %>
      <li style="margin-bottom: 5px;"><%= activity.description %></li>
    <% end %>

    <% if activities.size > 5 %>
      <li style="color: #999;">... and <%= activities.size - 5 %> more</li>
    <% end %>
  </ul>
<% end %>

<p style="margin-top: 30px;">
  <%= link_to "View all activity", account_activities_url(@account),
      style: "color: #0066cc; text-decoration: none;" %>
</p>

<p style="color: #999; font-size: 12px; margin-top: 30px;">
  You're receiving this because you opted in to daily digests.<br>
  <%= link_to "Manage preferences", account_settings_url(@account),
      style: "color: #999;" %>
</p>
```

---

## Email Preferences Model

Let users control which emails they receive, per account and per type.

### EmailPreference Model

```ruby
# app/models/email_preference.rb
class EmailPreference < ApplicationRecord
  belongs_to :user
  belongs_to :account

  enum :preference_type, {
    mentions: 0,
    comments: 1,
    assignments: 2,
    digests: 3
  }

  validates :preference_type, presence: true
  validates :preference_type, uniqueness: { scope: [:user_id, :account_id] }
end
```

### Migration

```ruby
# db/migrate/xxx_create_email_preferences.rb
class CreateEmailPreferences < ActiveRecord::Migration[8.0]
  def change
    create_table :email_preferences, id: :uuid do |t|
      t.references :user, null: false, type: :uuid
      t.references :account, null: false, type: :uuid
      t.integer :preference_type, null: false
      t.boolean :enabled, null: false, default: true

      t.timestamps
    end

    add_index :email_preferences, [:user_id, :account_id, :preference_type],
              unique: true, name: "index_email_prefs_on_user_account_type"
  end
end
```

### User Integration

```ruby
# app/models/user.rb (additions)
class User < ApplicationRecord
  has_many :email_preferences, dependent: :destroy

  enum :digest_frequency, {
    never: 0,
    daily: 1,
    weekly: 2
  }, prefix: true

  def email_preference_for(account, type)
    email_preferences.find_or_create_by(account: account, preference_type: type)
  end

  def wants_email?(account, type)
    preference = email_preferences.find_by(account: account, preference_type: type)
    preference.nil? || preference.enabled?
  end
end
```

### Preferences Controller with Tokenized Unsubscribe

```ruby
# app/controllers/email_preferences_controller.rb
class EmailPreferencesController < ApplicationController
  def index
    @preferences = Current.user.email_preferences
      .where(account: Current.account)
  end

  def update
    @preference = Current.user.email_preferences.find(params[:id])

    if @preference.update(preference_params)
      redirect_to account_email_preferences_path(Current.account),
                  notice: "Preferences updated"
    else
      render :index, status: :unprocessable_entity
    end
  end

  def unsubscribe
    token = params[:token]
    @user = User.find_by_unsubscribe_token(token)

    if @user && params[:account_id]
      @account = Account.find(params[:account_id])
      @user.email_preferences.where(account: @account).update_all(enabled: false)
      render :unsubscribed
    else
      render :invalid_token
    end
  end

  private

  def preference_params
    params.require(:email_preference).permit(:enabled)
  end
end
```

### Unsubscribe Links in Layout

```erb
<%# In app/views/layouts/mailer.html.erb footer %>
<% if @account && @user %>
  <br><br>
  <%= link_to "Unsubscribe",
      unsubscribe_url(token: @user.unsubscribe_token, account_id: @account.id),
      style: "color: #999;" %>
<% end %>
```

### Checking Preferences Before Sending

```ruby
# In model callbacks or services
def notify_subscribers
  card.subscribers.each do |subscriber|
    next if subscriber == creator
    next unless subscriber.wants_email?(account, :comments)

    CommentMailer.new_comment(self, subscriber).deliver_later
  end
end
```

---

## Notification Persistence Model

Track notifications with a polymorphic model for bundling and digest support.

### Notification Model

```ruby
# app/models/notification.rb
class Notification < ApplicationRecord
  belongs_to :user
  belongs_to :account
  belongs_to :notifiable, polymorphic: true

  enum :notification_type, {
    mention: 0,
    comment: 1,
    assignment: 2,
    invitation: 3
  }

  scope :unsent, -> { where(sent_at: nil) }
  scope :recent, -> { order(created_at: :desc) }
  scope :pending_digest, -> { unsent.where("created_at < ?", 1.hour.ago) }

  def mark_as_sent!
    update!(sent_at: Time.current)
  end

  def url
    case notifiable
    when Comment
      account_board_card_url(account, notifiable.card.board, notifiable.card)
    when Card
      account_board_card_url(account, notifiable.board, notifiable)
    when Membership
      account_url(account)
    end
  end

  def message
    case notification_type.to_sym
    when :mention
      "#{notifiable.creator.name} mentioned you in a comment"
    when :comment
      "New comment on #{notifiable.card.title}"
    when :assignment
      "#{notifiable.assigner.name} assigned you to #{notifiable.card.title}"
    when :invitation
      "#{notifiable.inviter.name} invited you to #{account.name}"
    end
  end
end
```

### Migration

```ruby
# db/migrate/xxx_create_notifications.rb
class CreateNotifications < ActiveRecord::Migration[8.0]
  def change
    create_table :notifications, id: :uuid do |t|
      t.references :user, null: false, type: :uuid
      t.references :account, null: false, type: :uuid
      t.references :notifiable, polymorphic: true, null: false, type: :uuid
      t.integer :notification_type, null: false
      t.datetime :sent_at
      t.datetime :read_at

      t.timestamps
    end

    add_index :notifications, [:user_id, :sent_at]
    add_index :notifications, [:user_id, :read_at]
    add_index :notifications, [:account_id, :created_at]
  end
end
```

### Creating Notifications from Model Callbacks

```ruby
# app/models/comment.rb
class Comment < ApplicationRecord
  after_create_commit :create_notifications

  private

  def create_notifications
    mentions.each do |mention|
      Notification.create!(
        user: mention.user,
        account: account,
        notifiable: self,
        notification_type: :mention
      )
    end

    card.subscribers.each do |subscriber|
      next if subscriber == creator

      Notification.create!(
        user: subscriber,
        account: account,
        notifiable: self,
        notification_type: :comment
      )
    end
  end
end
```

---

## Multi-Tenant Mail

Per-account from addresses and account context in footers.

### ApplicationMailer with Account Context

```ruby
# app/mailers/application_mailer.rb
class ApplicationMailer < ActionMailer::Base
  default from: "notifications@example.com"
  layout "mailer"

  before_action :attach_logo

  private

  def account_from_address(account)
    "#{account.name} <notifications@example.com>"
  end

  def account_reply_to(account)
    "#{account.slug}@reply.example.com"
  end

  def attach_logo
    attachments.inline["logo.png"] = File.read(
      Rails.root.join("app", "assets", "images", "logo.png")
    )
  end
end
```

### Using Account Context in Mailers

```ruby
# app/mailers/comment_mailer.rb
class CommentMailer < ApplicationMailer
  def mentioned(mention)
    @mention = mention
    @comment = mention.comment
    @card = mention.comment.card
    @account = mention.account

    mail(
      to: mention.user.email,
      subject: "#{mention.creator.name} mentioned you in #{@card.title}",
      from: account_from_address(@account),
      reply_to: account_reply_to(@account)
    )
  end
end
```

### Logo in Layout

```erb
<%# app/views/layouts/mailer.html.erb %>
<tr>
  <td style="text-align: center; padding: 20px;">
    <%= image_tag attachments["logo.png"].url,
        alt: "Logo",
        style: "width: 120px; height: auto;" %>
  </td>
</tr>
```

---

## Testing Digests and Preferences

### Integration Test: Digest Bundling

```ruby
# test/integration/email_delivery_test.rb
require "test_helper"

class EmailDeliveryTest < ActionDispatch::IntegrationTest
  test "bundles notifications into digest" do
    user = users(:alice)

    5.times do
      Notification.create!(
        user: user,
        account: accounts(:acme),
        notifiable: comments(:one),
        notification_type: :comment
      )
    end

    assert_emails 1 do
      NotificationBundler.new(user).send_digest
    end
  end
end
```

### System Test: Email Preferences

```ruby
# test/system/email_preferences_test.rb
require "application_system_test_case"

class EmailPreferencesTest < ApplicationSystemTestCase
  test "user can disable email notifications" do
    sign_in_as users(:alice)
    visit account_email_preferences_path(accounts(:acme))

    uncheck "Mentions"
    click_on "Save"

    assert_text "Preferences updated"

    comment = Comment.create!(
      card: cards(:one),
      body: "@alice check this out",
      creator: users(:bob),
      account: accounts(:acme)
    )

    assert_no_emails do
      comment.notify_mentions
    end
  end
end
```

---

## Performance Tips

1. **Always use `deliver_later`** — never block the request with synchronous delivery.
2. **Bundle notifications** — send one digest instead of N individual emails.
3. **Check preferences before enqueueing** — skip the job entirely when the user has opted out.
4. **Use Sidekiq's `:mailers` queue** — isolate email delivery from other background work.
5. **Keep templates simple** — do calculations in the mailer action, not the view.
6. **Batch find_each** — iterate users in batches for scheduled digest jobs.

## Boundaries

- **Always:** include unsubscribe links, respect email preferences, use `deliver_later`, include account context in from/reply-to addresses.
- **Ask first:** digest frequency (daily vs. weekly), whether to bundle or send immediately, cache expiration for digest aggregation.
- **Never:** send marketing emails from transactional mailers, deliver synchronously in production, send without checking preferences, expose sensitive data in email URLs.
