---
name: form-object-patterns
description: Creates form objects for complex form handling with TDD. Use when building multi-model forms, search forms, wizard forms, or when user mentions form objects, complex forms, virtual models, or non-persisted forms.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Form Object Patterns for Rails 8

## Overview

Form objects encapsulate complex form logic:
- Multi-model forms (user + profile + address)
- Search/filter forms (non-persisted)
- Wizard/multi-step forms
- Virtual attributes with validation
- Decoupled from ActiveRecord models

## When to Use Form Objects

| Scenario | Use Form Object? |
|----------|-----------------|
| Single model CRUD | No (use model) |
| Multi-model creation | Yes |
| Complex validations across models | Yes |
| Search/filter forms | Yes |
| Wizard/multi-step forms | Yes |
| API params transformation | Yes |
| Contact forms (no persistence) | Yes |

## TDD Workflow

```
Form Object Progress:
- [ ] Step 1: Define form requirements
- [ ] Step 2: Write form object spec (RED)
- [ ] Step 3: Run spec (fails)
- [ ] Step 4: Create form object
- [ ] Step 5: Run spec (GREEN)
- [ ] Step 6: Wire up controller
- [ ] Step 7: Create view form
```

## Project Structure

```
app/
├── forms/
│   ├── application_form.rb       # Base class
│   ├── registration_form.rb      # Multi-model
│   ├── search_form.rb            # Non-persisted
│   └── wizard/
│       ├── base_form.rb
│       ├── step_one_form.rb
│       └── step_two_form.rb
test/forms/
├── registration_form_test.rb
└── search_form_test.rb
```

## Base Form Class

```ruby
# app/forms/application_form.rb
class ApplicationForm
  include ActiveModel::Model
  include ActiveModel::Attributes
  include ActiveModel::Validations

  def self.model_name
    ActiveModel::Name.new(self, nil, name.chomp("Form"))
  end

  def persisted?
    false
  end

  # Override in subclasses
  def save
    return false unless valid?
    persist!
    true
  rescue ActiveRecord::RecordInvalid => e
    errors.add(:base, e.message)
    false
  end

  private

  def persist!
    raise NotImplementedError
  end
end
```

## Pattern 1: Multi-Model Registration Form

### Test First (RED)

```ruby
# test/forms/registration_form_test.rb
require "test_helper"

class RegistrationFormTest < ActiveSupport::TestCase
  test "validates presence of required fields" do
    form = RegistrationForm.new
    assert_not form.valid?
    assert form.errors.added?(:email, :blank)
    assert form.errors.added?(:password, :blank)
    assert form.errors.added?(:company_name, :blank)
  end

  test "validates password minimum length" do
    form = RegistrationForm.new(password: "short")
    form.valid?
    assert form.errors[:password].any? { |msg| msg.include?("minimum") }
  end

  test "save with valid params returns true" do
    form = RegistrationForm.new(valid_params)
    assert form.save
  end

  test "save creates a user" do
    form = RegistrationForm.new(valid_params)
    assert_difference "User.count", 1 do
      form.save
    end
  end

  test "save creates an account" do
    form = RegistrationForm.new(valid_params)
    assert_difference "Account.count", 1 do
      form.save
    end
  end

  test "save associates user with account" do
    form = RegistrationForm.new(valid_params)
    form.save
    assert_equal form.account, form.user.account
  end

  test "save persists created records" do
    form = RegistrationForm.new(valid_params)
    form.save
    assert_predicate form.user, :persisted?
    assert_predicate form.account, :persisted?
  end

  test "save with invalid params returns false" do
    form = RegistrationForm.new(email: "", password: "short")
    assert_not form.save
  end

  test "save with invalid params does not create records" do
    form = RegistrationForm.new(email: "", password: "short")
    assert_no_difference "User.count" do
      form.save
    end
  end

  test "save with invalid params has errors" do
    form = RegistrationForm.new(email: "", password: "short")
    form.save
    assert_not form.errors.empty?
  end

  test "save with duplicate email returns false with error" do
    User.create!(email_address: "taken@example.com", password: "password123")
    form = RegistrationForm.new(
      email: "taken@example.com",
      password: "password123",
      password_confirmation: "password123",
      company_name: "Acme Inc"
    )
    assert_not form.save
    assert_includes form.errors[:email], "has already been taken"
  end

  private

  def valid_params
    {
      email: "user@example.com",
      password: "password123",
      password_confirmation: "password123",
      company_name: "Acme Inc",
      phone: "0123456789"
    }
  end
end
```

### Implementation (GREEN)

```ruby
# app/forms/registration_form.rb
class RegistrationForm < ApplicationForm
  attribute :email, :string
  attribute :password, :string
  attribute :password_confirmation, :string
  attribute :company_name, :string
  attribute :phone, :string

  validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, presence: true, length: { minimum: 8 }
  validates :password_confirmation, presence: true
  validates :company_name, presence: true
  validate :passwords_match
  validate :email_unique

  attr_reader :user, :account

  private

  def persist!
    ActiveRecord::Base.transaction do
      @account = Account.create!(name: company_name)
      @user = User.create!(
        email_address: email,
        password: password,
        account: @account,
        phone: phone
      )
    end
  end

  def passwords_match
    return if password == password_confirmation
    errors.add(:password_confirmation, "doesn't match password")
  end

  def email_unique
    return unless User.exists?(email_address: email&.downcase)
    errors.add(:email, "has already been taken")
  end
end
```

## Pattern 2: Search/Filter Form

### Test First

```ruby
# test/forms/event_search_form_test.rb
require "test_helper"

class EventSearchFormTest < ActiveSupport::TestCase
  setup do
    @account = accounts(:one)
    @wedding = events(:wedding)
    @corporate = events(:corporate)
  end

  test "returns all account events without filters" do
    form = EventSearchForm.new(account: @account, params: {})
    assert_includes form.results, @wedding
    assert_includes form.results, @corporate
  end

  test "excludes other account events" do
    other_event = events(:other_account_event)
    form = EventSearchForm.new(account: @account, params: {})
    assert_not_includes form.results, other_event
  end

  test "filters by event type" do
    form = EventSearchForm.new(account: @account, params: { event_type: "wedding" })
    assert_includes form.results, @wedding
    assert_not_includes form.results, @corporate
  end

  test "searches by name" do
    form = EventSearchForm.new(account: @account, params: { query: "smith" })
    assert_includes form.results, @wedding
    assert_not_includes form.results, @corporate
  end

  test "filters by date range" do
    upcoming = Event.create!(account: @account, event_date: 2.weeks.from_now, name: "Upcoming")
    past = Event.create!(account: @account, event_date: 1.week.ago, name: "Past")

    form = EventSearchForm.new(
      account: @account,
      params: { start_date: Date.today, end_date: 1.month.from_now }
    )
    assert_includes form.results, upcoming
    assert_not_includes form.results, past
  end

  test "any_filters? returns true with filters" do
    form = EventSearchForm.new(account: @account, params: { query: "test" })
    assert form.any_filters?
  end

  test "any_filters? returns false without filters" do
    form = EventSearchForm.new(account: @account, params: {})
    assert_not form.any_filters?
  end
end
```

### Implementation

```ruby
# app/forms/event_search_form.rb
class EventSearchForm < ApplicationForm
  attribute :query, :string
  attribute :event_type, :string
  attribute :status, :string
  attribute :start_date, :date
  attribute :end_date, :date

  attr_reader :account

  def initialize(account:, params: {})
    @account = account
    super(params)
  end

  def results
    scope = account.events

    scope = apply_search(scope)
    scope = apply_type_filter(scope)
    scope = apply_status_filter(scope)
    scope = apply_date_filter(scope)

    scope.order(event_date: :desc)
  end

  def any_filters?
    [query, event_type, status, start_date, end_date].any?(&:present?)
  end

  # For form select options
  def event_type_options
    Event.event_types.keys.map { |t| [t.humanize, t] }
  end

  def status_options
    Event.statuses.keys.map { |s| [s.humanize, s] }
  end

  private

  def apply_search(scope)
    return scope if query.blank?
    scope.where("name ILIKE :q OR description ILIKE :q", q: "%#{sanitize_like(query)}%")
  end

  def apply_type_filter(scope)
    return scope if event_type.blank?
    scope.where(event_type: event_type)
  end

  def apply_status_filter(scope)
    return scope if status.blank?
    scope.where(status: status)
  end

  def apply_date_filter(scope)
    scope = scope.where("event_date >= ?", start_date) if start_date.present?
    scope = scope.where("event_date <= ?", end_date) if end_date.present?
    scope
  end

  def sanitize_like(term)
    term.gsub(/[%_]/) { |x| "\\#{x}" }
  end
end
```

## Pattern 3: Wizard/Multi-Step Form

### Base Wizard Form

```ruby
# app/forms/wizard/base_form.rb
module Wizard
  class BaseForm < ApplicationForm
    attribute :wizard_data, :string  # JSON storage

    def self.steps
      raise NotImplementedError
    end

    def current_step
      raise NotImplementedError
    end

    def next_step
      steps = self.class.steps
      current_index = steps.index(current_step)
      steps[current_index + 1]
    end

    def previous_step
      steps = self.class.steps
      current_index = steps.index(current_step)
      return nil if current_index.zero?
      steps[current_index - 1]
    end

    def first_step?
      current_step == self.class.steps.first
    end

    def last_step?
      current_step == self.class.steps.last
    end

    def progress_percentage
      steps = self.class.steps
      ((steps.index(current_step) + 1).to_f / steps.size * 100).round
    end
  end
end
```

### Step Forms

```ruby
# app/forms/wizard/event_step_one_form.rb
module Wizard
  class EventStepOneForm < BaseForm
    attribute :name, :string
    attribute :event_type, :string
    attribute :event_date, :date

    validates :name, presence: true
    validates :event_type, presence: true
    validates :event_date, presence: true

    def self.steps
      [:basics, :details, :vendors, :confirmation]
    end

    def current_step
      :basics
    end
  end
end

# app/forms/wizard/event_step_two_form.rb
module Wizard
  class EventStepTwoForm < BaseForm
    attribute :description, :string
    attribute :guest_count, :integer
    attribute :budget_cents, :integer

    validates :guest_count, numericality: { greater_than: 0 }, allow_nil: true

    def self.steps
      [:basics, :details, :vendors, :confirmation]
    end

    def current_step
      :details
    end
  end
end
```

## Pattern 4: Contact Form (No Persistence)

```ruby
# app/forms/contact_form.rb
class ContactForm < ApplicationForm
  attribute :name, :string
  attribute :email, :string
  attribute :subject, :string
  attribute :message, :string

  validates :name, presence: true
  validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :subject, presence: true
  validates :message, presence: true, length: { minimum: 10 }

  def save
    return false unless valid?
    deliver_email
    true
  end

  private

  def deliver_email
    ContactMailer.inquiry(
      name: name,
      email: email,
      subject: subject,
      message: message
    ).deliver_later
  end
end
```

## Controller Integration

```ruby
# app/controllers/registrations_controller.rb
class RegistrationsController < ApplicationController
  allow_unauthenticated_access

  def new
    @form = RegistrationForm.new
  end

  def create
    @form = RegistrationForm.new(registration_params)

    if @form.save
      start_new_session_for(@form.user)
      redirect_to dashboard_path, notice: t(".success")
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def registration_params
    params.require(:registration).permit(
      :email, :password, :password_confirmation,
      :company_name, :phone
    )
  end
end
```

## View Integration

```erb
<%# app/views/registrations/new.html.erb %>
<%= form_with model: @form, url: registrations_path do |f| %>
  <% if @form.errors.any? %>
    <div class="alert alert-error">
      <ul>
        <% @form.errors.full_messages.each do |message| %>
          <li><%= message %></li>
        <% end %>
      </ul>
    </div>
  <% end %>

  <div class="field">
    <%= f.label :email %>
    <%= f.email_field :email, autofocus: true %>
  </div>

  <div class="field">
    <%= f.label :password %>
    <%= f.password_field :password %>
  </div>

  <div class="field">
    <%= f.label :password_confirmation %>
    <%= f.password_field :password_confirmation %>
  </div>

  <div class="field">
    <%= f.label :company_name %>
    <%= f.text_field :company_name %>
  </div>

  <%= f.submit "Register" %>
<% end %>
```

### Search Form View

```erb
<%# app/views/events/_search_form.html.erb %>
<%= form_with model: @search_form, url: events_path, method: :get, local: true do |f| %>
  <div class="flex gap-4">
    <%= f.search_field :query, placeholder: "Search events..." %>
    <%= f.select :event_type, @search_form.event_type_options, include_blank: "All types" %>
    <%= f.select :status, @search_form.status_options, include_blank: "All statuses" %>
    <%= f.date_field :start_date %>
    <%= f.date_field :end_date %>
    <%= f.submit "Search" %>

    <% if @search_form.any_filters? %>
      <%= link_to "Clear", events_path, class: "btn-secondary" %>
    <% end %>
  </div>
<% end %>
```

## Checklist

- [ ] Spec written first (RED)
- [ ] Extends `ApplicationForm` or includes `ActiveModel::Model`
- [ ] Attributes declared with types
- [ ] Validations defined
- [ ] `#save` method with transaction (if multi-model)
- [ ] Controller uses form object
- [ ] View uses `form_with model: @form`
- [ ] Error handling in place
- [ ] All specs GREEN
