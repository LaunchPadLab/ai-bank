# Avo Testing Reference

Patterns for testing Avo 3.x admin panel components using Minitest: actions, filters, policies, CRUD operations, `Avo::Current`, and system tests with fixtures.

---

## Test Infrastructure

### Test Helper Setup

```ruby
# test/test_helper.rb
ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"

class ActiveSupport::TestCase
  fixtures :all

  def admin_user
    users(:admin)
  end
end
```

### System Test Base for Avo

```ruby
# test/system/avo/avo_system_test_case.rb
require "application_system_test_case"

class AvoSystemTestCase < ApplicationSystemTestCase
  include Avo::TestHelpers

  def setup
    sign_in_as_admin
  end

  private

  def sign_in_as_admin
    @admin = users(:admin)
    visit new_user_session_path
    fill_in "Email", with: @admin.email
    fill_in "Password", with: "password"
    click_button "Log in"
  end

  def visit_avo_resource(resource_name)
    visit "/avo/resources/#{resource_name}"
  end

  def visit_avo_resource_show(resource_name, id)
    visit "/avo/resources/#{resource_name}/#{id}"
  end

  def visit_avo_resource_edit(resource_name, id)
    visit "/avo/resources/#{resource_name}/#{id}/edit"
  end

  def visit_avo_resource_new(resource_name)
    visit "/avo/resources/#{resource_name}/new"
  end
end
```

### Avo Testing Helpers

Avo provides `Avo::TestHelpers` with methods for opening/closing datepickers, choosing dates, saving records, adding/removing tags, and selecting UI elements. Include via `include Avo::TestHelpers` in your system test base class.

Source: [avo/lib/avo/test_helpers.rb](https://github.com/avo-hq/avo/blob/main/lib/avo/test_helpers.rb)

### Fixtures

```yaml
# test/fixtures/users.yml
admin:
  first_name: Admin
  last_name: User
  email: admin@example.com
  password_digest: <%= BCrypt::Password.create("password") %>
  is_admin: true

regular:
  first_name: Regular
  last_name: User
  email: regular@example.com
  password_digest: <%= BCrypt::Password.create("password") %>
  is_admin: false
```

---

## Testing Authorization Policies (Pundit)

Policy tests are the most critical Avo tests — they verify who can do what.

### Basic CRUD Policy Test

```ruby
# test/policies/post_policy_test.rb
require "test_helper"

class PostPolicyTest < ActiveSupport::TestCase
  def setup
    @admin = users(:admin)
    @regular = users(:regular)
    @post = posts(:published)
  end

  test "admin can index posts" do
    assert PostPolicy.new(@admin, Post).index?
  end

  test "admin can create posts" do
    assert PostPolicy.new(@admin, Post).create?
  end

  test "regular user cannot create posts" do
    assert_not PostPolicy.new(@regular, Post).create?
  end

  test "admin can edit any post" do
    assert PostPolicy.new(@admin, @post).edit?
  end

  test "admin can destroy posts" do
    assert PostPolicy.new(@admin, @post).destroy?
  end

  test "admin can act on posts" do
    assert PostPolicy.new(@admin, @post).act_on?
  end

  test "admin can search posts" do
    assert PostPolicy.new(@admin, Post).search?
  end
end
```

### Association Policy Test

When `config.explicit_authorization = true`, you must add `view_<association>?` methods or association sections are hidden.

```ruby
# test/policies/post_policy_associations_test.rb
require "test_helper"

class PostPolicyAssociationsTest < ActiveSupport::TestCase
  def setup
    @admin = users(:admin)
    @post = posts(:published)
    @comment = comments(:on_published_post)
  end

  test "admin can view comments on post" do
    assert PostPolicy.new(@admin, @comment).view_comments?
  end

  test "admin can create comments on post" do
    assert PostPolicy.new(@admin, @post).create_comments?
  end

  test "admin can attach comments" do
    assert PostPolicy.new(@admin, @post).attach_comments?
  end

  test "admin can detach comments" do
    assert PostPolicy.new(@admin, @comment).detach_comments?
  end
end
```

### Policy Scope Test

```ruby
# test/policies/post_policy_scope_test.rb
require "test_helper"

class PostPolicyScopeTest < ActiveSupport::TestCase
  test "admin sees all posts" do
    scope = PostPolicy::Scope.new(users(:admin), Post).resolve
    assert_equal Post.count, scope.count
  end

  test "regular user sees only published posts" do
    scope = PostPolicy::Scope.new(users(:regular), Post).resolve
    assert scope.all? { |post| post.published_at.present? }
  end
end
```

---

## Testing Actions

Actions are pure Ruby objects — test them without a browser.

```ruby
# test/avo/actions/publish_post_test.rb
require "test_helper"

class Avo::Actions::PublishPostTest < ActiveSupport::TestCase
  def setup
    @admin = users(:admin)
    @post = posts(:draft)
    @resource = Avo::Resources::Post.new.hydrate(model: @post)
  end

  test "publishes a single post" do
    action = Avo::Actions::PublishPost.new(
      resource: @resource,
      user: @admin,
      view: :edit
    )

    args = {
      fields: { published_at: Time.current },
      current_user: @admin,
      resource: @resource,
      query: [@post]
    }

    action.stub(:succeed, nil) do
      action.handle(**args)
    end

    @post.reload
    assert_not_nil @post.published_at
  end

  test "publishes multiple posts" do
    draft_posts = [posts(:draft), posts(:draft_two)]

    action = Avo::Actions::PublishPost.new(
      resource: @resource,
      user: @admin,
      view: :edit
    )

    action.stub(:succeed, nil) do
      action.handle(
        fields: { published_at: Time.current },
        current_user: @admin,
        resource: @resource,
        query: draft_posts
      )
    end

    draft_posts.each { |p| assert_not_nil p.reload.published_at }
  end
end
```

### Testing Actions with Redirects

```ruby
test "action redirects after success" do
  action = Avo::Actions::ArchivePost.new(
    resource: @resource,
    user: @admin,
    view: :edit
  )

  result = nil
  action.stub(:succeed, ->(msg) { result = msg }) do
    action.stub(:redirect_to, nil) do
      action.handle(
        fields: {},
        current_user: @admin,
        resource: @resource,
        query: [@post]
      )
    end
  end
end
```

---

## Testing Filters

### Unit Testing Basic Filters

```ruby
# test/avo/filters/published_filter_test.rb
require "test_helper"

class Avo::Filters::PublishedTest < ActiveSupport::TestCase
  def setup
    @filter = Avo::Filters::Published.new
  end

  test "returns correct options" do
    options = @filter.options
    assert_includes options.keys, :published
    assert_includes options.keys, :unpublished
  end

  test "filters published posts" do
    query = Post.all
    result = @filter.apply(nil, query, "published")
    assert result.all? { |post| post.published_at.present? }
  end

  test "filters unpublished posts" do
    query = Post.all
    result = @filter.apply(nil, query, "unpublished")
    assert result.all? { |post| post.published_at.nil? }
  end

  test "returns all when no value" do
    query = Post.all
    result = @filter.apply(nil, query, nil)
    assert_equal Post.count, result.count
  end
end
```

### Testing Boolean Filters

```ruby
# test/avo/filters/featured_filter_test.rb
require "test_helper"

class Avo::Filters::FeaturedTest < ActiveSupport::TestCase
  test "filters featured records" do
    filter = Avo::Filters::Featured.new
    result = filter.apply(nil, Post.all, { "is_featured" => true, "is_unfeatured" => false })
    assert result.all?(&:is_featured)
  end

  test "returns all when both selected" do
    filter = Avo::Filters::Featured.new
    result = filter.apply(nil, Post.all, { "is_featured" => true, "is_unfeatured" => true })
    assert_equal Post.count, result.count
  end
end
```

---

## Testing CRUD Operations (System Tests)

```ruby
# test/system/avo/posts_test.rb
require_relative "../avo_system_test_case"

class Avo::PostsSystemTest < AvoSystemTestCase
  test "index page lists posts" do
    visit_avo_resource("posts")
    assert_text "Posts"
    assert_selector "table tbody tr", minimum: 1
  end

  test "show page displays post details" do
    post = posts(:published)
    visit_avo_resource_show("posts", post.id)
    assert_text post.name
  end

  test "creates a new post" do
    visit_avo_resource_new("posts")
    fill_in "Name", with: "New Post Title"
    fill_in "Body", with: "Post body content"
    click_button "Save"
    assert_text "Post was successfully created"
  end

  test "edits an existing post" do
    post = posts(:published)
    visit_avo_resource_edit("posts", post.id)
    fill_in "Name", with: "Updated Post Title"
    click_button "Save"
    assert_text "Post was successfully updated"
    assert_text "Updated Post Title"
  end

  test "deletes a post" do
    post = posts(:draft)
    visit_avo_resource_show("posts", post.id)
    accept_confirm { click_button "Delete" }
    assert_text "Record destroyed"
  end
end
```

---

## `Avo::Current` in Tests

`Avo::Current` is based on `ActiveSupport::CurrentAttributes` and holds per-request state.

### Available Attributes

| Attribute | Description |
|-----------|-------------|
| `Avo::Current.user` | Current user from `current_user_method` |
| `Avo::Current.params` | `request.params` |
| `Avo::Current.request` | Rails `request` |
| `Avo::Current.context` | Custom context from initializer |
| `Avo::Current.view_context` | `ActionView::Rendering` instance |
| `Avo::Current.locale` | App locale |
| `Avo::Current.tenant_id` | Tenant ID for multitenancy |
| `Avo::Current.tenant` | Tenant object |

### Setting `Avo::Current` in Tests

```ruby
# In unit tests where Avo::Current isn't set by a request cycle
test "uses Avo::Current context" do
  Avo::Current.user = users(:admin)
  Avo::Current.context = { foo: "bar" }

  assert_equal "bar", Avo::Current.context[:foo]
  assert Avo::Current.user_is_admin?
ensure
  Avo::Current.reset
end
```

---

## Testing Resource Configuration

```ruby
# test/avo/resources/post_resource_test.rb
require "test_helper"

class Avo::Resources::PostTest < ActiveSupport::TestCase
  test "resource has expected title" do
    resource = Avo::Resources::Post.new
    assert_equal :name, resource.class.title
  end

  test "resource hydrates correctly" do
    post = posts(:published)
    resource = Avo::Resources::Post.new.hydrate(model: post)
    assert_equal post, resource.record
  end
end
```

---

## Test File Organization

```
test/
├── avo/
│   ├── actions/
│   │   └── publish_post_test.rb
│   ├── filters/
│   │   ├── featured_filter_test.rb
│   │   └── published_filter_test.rb
│   └── resources/
│       └── post_resource_test.rb
├── policies/
│   ├── post_policy_test.rb
│   ├── post_policy_associations_test.rb
│   └── post_policy_scope_test.rb
└── system/
    └── avo/
        ├── avo_system_test_case.rb
        └── posts_test.rb
```
