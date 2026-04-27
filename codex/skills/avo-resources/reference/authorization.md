# Avo Authorization Reference

Avo uses [Pundit](https://github.com/varvet/pundit) as its default authorization client.
Authorization controls which resources, actions, and associations users can access.

---

## Setup

### 1. Add Pundit to Gemfile

```ruby
gem "pundit"
```

### 2. Install Pundit

```bash
bin/rails g pundit:install
```

### 3. Configure Avo

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.current_user_method = :current_user
  config.authorization_client = :pundit
end
```

### 4. Generate Policies

```bash
bin/rails g pundit:policy Post
```

---

## Standard Policy Methods

Every policy class supports these methods to control resource access:

| Method      | Controls                                                          |
|-------------|-------------------------------------------------------------------|
| `index?`    | Sidebar visibility (auto-generated menu) and Index page access    |
| `show?`     | Show icon on resource row and Show page access                    |
| `create?`   | "Create new" button, Save button on /new, association create      |
| `new?`      | Whether user can save a new resource (has access to `record`)     |
| `edit?`     | Edit button on resource row and Edit page access                  |
| `update?`   | Whether user can save updates (has access to `record`)            |
| `destroy?`  | Delete button visibility and destroy action                       |
| `act_on?`   | Actions dropdown button visibility                                |
| `reorder?`  | Record reordering buttons visibility                              |
| `search?`   | Resource search input on top of page                              |
| `preview?`  | Access to the preview endpoint (does NOT hide the preview field)  |

### Complete Policy Example

```ruby
# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    true
  end

  def create?
    user.admin? || user.editor?
  end

  def new?
    create?
  end

  def update?
    user.admin? || record.user_id == user.id
  end

  def edit?
    update?
  end

  def destroy?
    user.admin?
  end

  def act_on?
    user.admin?
  end

  def reorder?
    user.admin?
  end

  def search?
    true
  end

  def preview?
    true
  end
end
```

---

## Policy Scopes

Scopes restrict which records appear on the Index view.

```ruby
class PostPolicy < ApplicationPolicy
  class Scope < Scope
    def resolve
      if user.admin?
        scope.all
      else
        scope.where(published: true)
      end
    end
  end
end
```

### Important: Scopes and Associations

Policy scopes only apply to the resource's **Index** view. They do NOT apply to
association views (`has_many` tables on a parent record's page).

To scope association records, use the `scope` option on the association field:

```ruby
# app/avo/resources/post.rb
class Avo::Resources::Post < Avo::BaseResource
  def fields
    field :comments, as: :has_many,
      scope: -> { Pundit.policy_scope(parent, query) }
  end
end
```

---

## Association Authorization

Association policy methods control attach/detach/view/edit/create/destroy buttons
on association panels. They are defined in the **parent resource's** policy.

### Naming Convention

Use the **same pluralization** as the association name:

```ruby
# For: has_many :comments
# Correct:   attach_comments?
# INCORRECT: attach_comment?
```

### Association Policy Methods

Using `Post has_many :comments` as the example:

| Method              | Controls                        | `record` variable                   |
|---------------------|---------------------------------|-------------------------------------|
| `attach_comments?`  | "Attach comment" button         | Parent record (`Post` instance)     |
| `detach_comments?`  | Detach button on each row       | Row record (`Comment` instance)     |
| `view_comments?`    | Entire association panel        | Parent record (`Post` instance)     |
| `show_comments?`    | View button on each row         | Row record (`Comment` instance)     |
| `edit_comments?`    | Edit button on each row         | Row record (`Comment` instance)     |
| `create_comments?`  | "Create comment" button         | Parent record (`Post` instance)     |
| `destroy_comments?` | Delete button on each row       | Row record (`Comment` instance)     |
| `act_on_comments?`  | Actions dropdown                | Parent record (`Post` instance)     |
| `reorder_comments?` | Reorder buttons on has_many     | Parent record (`Post` instance)     |

### Difference Between `view_` and `show_`

- `view_comments?` controls whether the **entire comments listing** appears on the
  Post's page. The `record` is the parent `Post`.
- `show_comments?` controls whether the **view button** is visible on each individual
  comment row. The `record` is each `Comment`.

### Full Association Policy Example

```ruby
# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  # Standard methods...
  def index? = true
  def show? = true
  def create? = user.admin? || user.editor?
  def edit? = user.admin? || record.user_id == user.id
  def update? = edit?
  def destroy? = user.admin?

  # Association: has_many :comments
  def attach_comments?
    user.admin?
  end

  def detach_comments?
    user.admin? || record.user_id == user.id
  end

  def view_comments?
    true
  end

  def show_comments?
    true
  end

  def edit_comments?
    user.admin? || record.user_id == user.id
  end

  def create_comments?
    user.admin? || user.editor?
  end

  def destroy_comments?
    user.admin?
  end

  def act_on_comments?
    user.admin?
  end

  def reorder_comments?
    user.admin?
  end
end
```

---

## Removing Duplication with PolicyHelpers

When association policy methods duplicate the child resource's policy logic, use
`PolicyHelpers` to auto-delegate.

### Setup

Include `Avo::Pro::Concerns::PolicyHelpers` in `ApplicationPolicy`:

```ruby
# app/policies/application_policy.rb
class ApplicationPolicy
  include Avo::Pro::Concerns::PolicyHelpers

  attr_reader :user, :record

  def initialize(user, record)
    @user = user
    @record = record
  end
end
```

### Usage

```ruby
# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  inherit_association_from_policy :comments, CommentPolicy
end
```

This single line generates all association methods by delegating to `CommentPolicy`:

```ruby
# Auto-generated methods:
def create_comments?  = CommentPolicy.new(user, record).create?
def edit_comments?    = CommentPolicy.new(user, record).edit?
def update_comments?  = CommentPolicy.new(user, record).update?
def destroy_comments? = CommentPolicy.new(user, record).destroy?
def show_comments?    = CommentPolicy.new(user, record).show?
def reorder_comments? = CommentPolicy.new(user, record).reorder?
def act_on_comments?  = CommentPolicy.new(user, record).act_on?
def view_comments?    = CommentPolicy.new(user, record).index?
def attach_comments?  = CommentPolicy.new(user, record).attach?   # Since 3.10.0
def detach_comments?  = CommentPolicy.new(user, record).detach?   # Since 3.10.0
```

### Override Individual Methods

You can still override any auto-generated method:

```ruby
class PostPolicy < ApplicationPolicy
  inherit_association_from_policy :comments, CommentPolicy

  def destroy_comments?
    false
  end
end
```

### Manual Delegation (Without PolicyHelpers)

```ruby
class PostPolicy < ApplicationPolicy
  def edit_comments?
    Pundit.policy!(user, record).edit?
  end
end
```

---

## Attachment Authorization

Control file upload, download, and delete permissions per-attachment.
Method names follow the pattern: `{action}_{attachment_name}?`

| Method             | Controls                    |
|--------------------|-----------------------------|
| `upload_{name}?`   | Whether user can upload     |
| `download_{name}?` | Whether user can download   |
| `delete_{name}?`   | Whether user can delete     |

Both `record` and `user` are available in these methods.

### Example

```ruby
class PostPolicy < ApplicationPolicy
  def upload_cover_photo?
    user.admin? || user.editor?
  end

  def download_cover_photo?
    true
  end

  def delete_cover_photo?
    user.admin?
  end

  def upload_audio?
    user.admin?
  end

  def download_audio?
    true
  end

  def delete_audio?
    user.admin?
  end
end
```

### Actions Inherit Attachment Authorization

Attachment authorization methods also apply to file fields in Avo actions that run
on the same resource. If `upload_file?` is defined in `PostPolicy` and an action on
`Avo::Resources::Post` has `field :file, as: :file`, the same `upload_file?` method
authorizes the upload.

### Bulk Attachment Authorization

Use meta-programming to authorize multiple attachments at once:

```ruby
class PostPolicy < ApplicationPolicy
  [:cover_photo, :audio].each do |file|
    [:upload, :download, :delete].each do |action|
      define_method "#{action}_#{file}?" do
        user.admin? || user.editor?
      end
    end
  end
end
```

### Attachment Policy Extension Pattern

For cleaner code, add a `method_missing` helper to `ApplicationPolicy` and define
attachment permissions declaratively:

```ruby
# app/policies/application_policy.rb
class ApplicationPolicy
  def method_missing(method_name, *args)
    if method_name.to_s =~ /^(upload|delete|download)_(.+)\?$/
      action = Regexp.last_match(1).to_sym
      attachment = Regexp.last_match(2).to_sym

      if attachment_concerns.key?(attachment) && attachment_concerns[attachment].key?(action)
        return attachment_concerns[attachment][action]
      end
    end

    super
  end

  def attachment_concerns
    {}
  end
end

# app/policies/organization_policy.rb
class OrganizationPolicy < ApplicationPolicy
  def attachment_concerns
    {
      logo: {
        upload: update?,
        delete: update?,
        download: show?
      },
      banner: {
        upload: user.admin?,
        delete: user.admin?,
        download: true
      }
    }
  end
end
```

---

## Custom Authorization Methods

Rename Avo's default policy method names to avoid conflicts with existing policies:

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.authorization_methods = {
    index: 'avo_index?',
    show: 'avo_show?',
    edit: 'avo_edit?',
    new: 'avo_new?',
    update: 'avo_update?',
    create: 'avo_create?',
    destroy: 'avo_destroy?',
    search: 'avo_search?',
  }
end
```

Now policies use `avo_index?` instead of `index?`:

```ruby
class PostPolicy < ApplicationPolicy
  def avo_index?
    true
  end

  def avo_show?
    true
  end

  def avo_create?
    user.admin?
  end
end
```

---

## Authorize Custom Actions Using Policy

Delegate field-level authorization to the policy class:

```ruby
# app/avo/resources/product.rb
class Avo::Resources::Product < Avo::BaseResource
  def fields
    field :amount,
      as: :money,
      currencies: %w[USD],
      disabled: -> { !@resource.authorization.authorize_action(:amount?, raise_exception: false) }
  end
end

# app/policies/product_policy.rb
class ProductPolicy < ApplicationPolicy
  def amount?
    user.admin?
  end
end
```

---

## Custom Policy Per Resource

Override the inferred policy for a resource:

```ruby
# app/avo/resources/photo_comment.rb
class Avo::Resources::PhotoComment < Avo::BaseResource
  self.model_class = "Comment"
  self.authorization_policy = PhotoCommentPolicy
end
```

---

## Explicit Authorization (Deny by Default)

Controls how missing policy classes or methods are handled.

| Value   | Missing policy/method behavior           |
|---------|------------------------------------------|
| `true`  | Unauthorized (deny by default)           |
| `false` | Authorized (allow by default)            |
| `Proc`  | Custom logic via `Avo::ExecutionContext` |

- **New apps (3.13.4+)**: defaults to `true` (secure by default)
- **Existing apps upgrading**: defaults to `false` (backward compatible)

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.explicit_authorization = true
end
```

With a Proc:

```ruby
Avo.configure do |config|
  config.explicit_authorization = -> {
    current_user.access_to_admin_panel? && !current_user.admin?
  }
end
```

### Behavior Examples

When `explicit_authorization = true`:
- Resource with **no policy class**: all actions **denied**
- Policy with only `show?` defined: `show?` works, `index?` **denied**

When `explicit_authorization = false`:
- Resource with **no policy class**: all actions **allowed**
- Policy with only `show?` defined: `show?` works, `index?` **allowed**

---

## Raise Errors on Missing Policies

Force every resource to have an explicit policy class:

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.raise_error_on_missing_policy = true
end
```

Without this, resources missing policies are silently authorized. With it, a missing
`UserPolicy` for `Avo::Resources::User` raises an error.

**Recommendation**: Enable in development to catch missing policies. In production
with `explicit_authorization = true`, prefer showing an unauthorized message over
raising errors.

---

## Custom Authorization Clients

Replace Pundit with a custom authorization backend.

### Configuration

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.authorization_client = 'Services::AuthorizationClients::CustomClient'
end
```

### Required Client Methods

Your client must implement these methods:

```ruby
class Services::AuthorizationClients::CustomClient
  # Authorize a user to perform an action on a record
  def authorize(user, record, action, policy_class: nil)
    # Raise NoPolicyError if policy not found
    # Raise NotAuthorizedError if not authorized
  end

  # Return the policy for a user/record pair
  def policy(user, record)
    # Return the policy instance
  end

  # Return the policy, raising if not found
  def policy!(user, record)
    # Return the policy instance or raise NoPolicyError
  end

  # Apply a scope to a query
  def apply_policy(user, model, policy_class: nil)
    # Return scoped query
  end
end
```

Reference implementation:
[Pundit client source](https://github.com/avo-hq/avo/blob/main/lib/avo/services/authorization_clients/pundit_client.rb)

---

## Authorization Logs

Avo logs unauthorized actions for debugging.

### Development Logs

```
[Avo->] Unauthorized action 'reorder?' for 'UserPolicy'
user: gid://dummy/User/20
record: gid://dummy/User/31
```

### Production Logs

```
[Avo->] Unauthorized action 'act_on?' for 'UserPolicy'
```

### Look Up Records from Global IDs

```ruby
gid = "gid://dummy/User/20"
user = GlobalID::Locator.locate(gid)
```

---

## Quick Reference: Complete Policy Template

```ruby
class PostPolicy < ApplicationPolicy
  class Scope < Scope
    def resolve
      if user.admin?
        scope.all
      else
        scope.where(published: true)
      end
    end
  end

  # Standard resource methods
  def index?  = true
  def show?   = true
  def create? = user.admin? || user.editor?
  def new?    = create?
  def edit?   = user.admin? || record.user_id == user.id
  def update? = edit?
  def destroy? = user.admin?

  # Extra resource methods
  def act_on?  = user.admin?
  def reorder? = user.admin?
  def search?  = true
  def preview? = true

  # Association methods (has_many :comments)
  inherit_association_from_policy :comments, CommentPolicy

  # Attachment methods
  [:cover_photo, :audio].each do |file|
    [:upload, :download, :delete].each do |action|
      define_method "#{action}_#{file}?" do
        user.admin? || user.editor?
      end
    end
  end
end
```

---

## Configuration Summary

```ruby
# config/initializers/avo.rb
Avo.configure do |config|
  config.current_user_method = :current_user
  config.authorization_client = :pundit
  config.explicit_authorization = true
  config.raise_error_on_missing_policy = true   # dev only recommended

  # Optional: rename policy methods
  # config.authorization_methods = {
  #   index: 'avo_index?',
  #   show: 'avo_show?',
  #   ...
  # }
end
```
