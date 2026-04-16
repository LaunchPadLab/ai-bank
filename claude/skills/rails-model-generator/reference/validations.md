# Rails Validation Patterns Reference

## Standard Validations

### Presence

```ruby
validates :name, presence: true
validates :email, presence: { message: "is required" }
```

**Test:**
```ruby
test "requires name" do
  record = ModelName.new(name: nil)
  assert_not record.valid?
  assert_includes record.errors[:name], "can't be blank"
end
```

### Uniqueness

```ruby
validates :email, uniqueness: true
validates :email, uniqueness: { case_sensitive: false }
validates :slug, uniqueness: { scope: :organization_id }
validates :email, uniqueness: { conditions: -> { where(deleted_at: nil) } }
```

**Test:**
```ruby
test "requires unique email (case insensitive)" do
  existing = model_names(:one)
  record = ModelName.new(email: existing.email.upcase)
  assert_not record.valid?
  assert_includes record.errors[:email], "has already been taken"
end

test "requires unique slug scoped to organization" do
  existing = model_names(:one)
  record = ModelName.new(slug: existing.slug, organization: existing.organization)
  assert_not record.valid?
end
```

### Length

```ruby
validates :name, length: { maximum: 100 }
validates :bio, length: { minimum: 10, maximum: 500 }
validates :pin, length: { is: 4 }
validates :tags, length: { in: 1..5 }
```

**Test:**
```ruby
test "enforces max length on name" do
  record = ModelName.new(name: "a" * 101)
  assert_not record.valid?
  assert_includes record.errors[:name], "is too long (maximum is 100 characters)"
end

test "enforces min/max length on bio" do
  record = ModelName.new(bio: "short")
  assert_not record.valid?
  assert_includes record.errors[:bio], "is too short (minimum is 10 characters)"
end

test "enforces exact length on pin" do
  record = ModelName.new(pin: "123")
  assert_not record.valid?
  assert_includes record.errors[:pin], "is the wrong length (should be 4 characters)"
end
```

### Format

```ruby
validates :email, format: { with: URI::MailTo::EMAIL_REGEXP }
validates :phone, format: { with: /\A\+?[\d\s-]+\z/ }
validates :slug, format: { with: /\A[a-z0-9-]+\z/, message: "only allows lowercase letters, numbers, and hyphens" }
```

**Test:**
```ruby
test "allows valid email format" do
  record = ModelName.new(email: "test@example.com")
  record.valid?
  assert_empty record.errors[:email]
end

test "rejects invalid email format" do
  record = ModelName.new(email: "invalid-email")
  assert_not record.valid?
  assert_includes record.errors[:email], "is invalid"
end
```

### Numericality

```ruby
validates :age, numericality: { only_integer: true, greater_than: 0 }
validates :price, numericality: { greater_than_or_equal_to: 0 }
validates :quantity, numericality: { only_integer: true, in: 1..100 }
```

**Test:**
```ruby
test "requires age to be a positive integer" do
  record = ModelName.new(age: -1)
  assert_not record.valid?
  assert_includes record.errors[:age], "must be greater than 0"
end

test "requires price to be non-negative" do
  record = ModelName.new(price: -0.01)
  assert_not record.valid?
  assert_includes record.errors[:price], "must be greater than or equal to 0"
end
```

### Inclusion/Exclusion

```ruby
validates :status, inclusion: { in: %w[draft published archived] }
validates :role, inclusion: { in: :allowed_roles }
validates :username, exclusion: { in: %w[admin root system] }
```

**Test:**
```ruby
test "requires status to be a valid value" do
  record = ModelName.new(status: "invalid")
  assert_not record.valid?
  assert_includes record.errors[:status], "is not included in the list"
end

test "rejects reserved usernames" do
  record = ModelName.new(username: "admin")
  assert_not record.valid?
  assert_includes record.errors[:username], "is reserved"
end
```

### Acceptance

```ruby
validates :terms, acceptance: true
validates :terms, acceptance: { accept: ['yes', 'true', '1'] }
```

### Confirmation

```ruby
validates :password, confirmation: true
# Requires :password_confirmation attribute in form
```

## Conditional Validations

### With If/Unless

```ruby
validates :phone, presence: true, if: :requires_phone?
validates :company, presence: true, unless: :individual?
validates :bio, length: { minimum: 50 }, if: -> { featured? }
```

**Test:**
```ruby
test "requires phone when requires_phone? is true" do
  record = ModelName.new(phone: nil)
  record.stub(:requires_phone?, true) do
    assert_not record.valid?
    assert_includes record.errors[:phone], "can't be blank"
  end
end
```

### With On (Context)

```ruby
validates :password, presence: true, on: :create
validates :reason, presence: true, on: :archive
```

**Test:**
```ruby
test "requires password on create" do
  record = ModelName.new(password: nil)
  assert_not record.valid?(:create)
  assert_includes record.errors[:password], "can't be blank"
end
```

## Custom Validations

### Custom Method

```ruby
class User < ApplicationRecord
  validate :email_domain_allowed

  private

  def email_domain_allowed
    return if email.blank?

    domain = email.split('@').last
    unless allowed_domains.include?(domain)
      errors.add(:email, "domain is not allowed")
    end
  end
end
```

**Test:**
```ruby
test "allows valid email domain" do
  user = User.new(email: "test@allowed.com")
  user.valid?
  assert_empty user.errors[:email]
end

test "rejects disallowed email domain" do
  user = User.new(email: "test@blocked.com")
  assert_not user.valid?
  assert_includes user.errors[:email], "domain is not allowed"
end
```

### Custom Validator Class

```ruby
# app/validators/email_domain_validator.rb
class EmailDomainValidator < ActiveModel::EachValidator
  def validate_each(record, attribute, value)
    return if value.blank?

    domain = value.split('@').last
    unless options[:allowed].include?(domain)
      record.errors.add(attribute, options[:message] || "domain not allowed")
    end
  end
end

# Usage in model:
validates :email, email_domain: { allowed: %w[company.com], message: "must be company email" }
```

## Association Validations

```ruby
validates :organization, presence: true
validates_associated :profile  # Validates the associated record too

# With nested attributes
accepts_nested_attributes_for :addresses, allow_destroy: true
validates :addresses, length: { minimum: 1, message: "must have at least one address" }
```

## Database-Level Constraints

Always pair validations with database constraints:

```ruby
# Migration
add_column :users, :email, :string, null: false
add_index :users, :email, unique: true
add_check_constraint :users, 'age >= 0', name: 'age_non_negative'

# Model
validates :email, presence: true, uniqueness: true
validates :age, numericality: { greater_than_or_equal_to: 0 }
```

## Common Email Regex Patterns

```ruby
# Simple (recommended for most cases)
URI::MailTo::EMAIL_REGEXP

# More permissive
/\A[^@\s]+@[^@\s]+\z/

# Strict RFC 5322
/\A(?=[a-z0-9@.!#$%&'*+\/=?^_'{|}~-]{6,254}\z).../ # (very long)
```

## Performance Tips

1. **Order validations by cost**: Put cheap validations first
2. **Use `on:` to skip validations**: Don't validate password on every save
3. **Avoid N+1 in custom validations**: Cache lookups
4. **Use database constraints**: They're faster than Rails validations
