# Avo Associations Reference

Avo maps Active Record associations to interactive UI panels on resource pages.
Always set `inverse_of` on your model associations for correct behavior.

---

## Belongs To

```ruby
field :user, as: :belongs_to
```

On Index/Show views: renders a link to the associated record using `self.title`.
On Edit/New views: renders a dropdown (or searchable field) to select a record.

### Searchable Belongs To

Replace the dropdown with a search input when there are many records:

```ruby
class Avo::Resources::Comment < Avo::BaseResource
  def fields
    field :user, as: :belongs_to, searchable: true
  end
end
```

The target resource must have `search` configured:

```ruby
class Avo::Resources::User < Avo::BaseResource
  self.search = {
    query: -> {
      query.ransack(id_eq: q, name_cont: q, email_cont: q, m: "or").result(distinct: false)
    }
  }
end
```

### Polymorphic Belongs To

Add `polymorphic_as` and `types` to declare polymorphic associations:

```ruby
class Avo::Resources::Comment < Avo::BaseResource
  def fields
    field :commentable,
      as: :belongs_to,
      polymorphic_as: :commentable,
      types: [::Post, ::Project]
  end
end
```

With help text for the type selector:

```ruby
field :reviewable,
  as: :belongs_to,
  polymorphic_as: :reviewable,
  types: [::Post, ::Project, ::Team],
  polymorphic_help: "Choose the type of record to review",
  help: "Choose the record you need."
```

Searchable polymorphic:

```ruby
field :commentable,
  as: :belongs_to,
  polymorphic_as: :commentable,
  types: [::Post, ::Project],
  searchable: true
```

Each polymorphic type's resource must have `search` configured.

### Allow Via Detaching

When visiting a record through an association, the `belongs_to` field is disabled
by default. Enable editing with `allow_via_detaching`:

```ruby
field :commentable,
  as: :belongs_to,
  polymorphic_as: :commentable,
  types: [::Post, ::Project],
  allow_via_detaching: true
```

### Attach Scope (Belongs To)

Filter which records appear in the dropdown/search:

```ruby
field :user,
  as: :belongs_to,
  attach_scope: -> { query.non_admins }
```

With access to the parent record:

```ruby
field :user,
  as: :belongs_to,
  attach_scope: -> { query.where(organization_id: parent.organization_id) }
```

### Use Resource

Display or redirect using a different Avo resource:

```ruby
field :user,
  as: :belongs_to,
  use_resource: Avo::Resources::AdminUser
```

### Can Create

Control the inline creation link on forms:

```ruby
field :user, as: :belongs_to, can_create: true
```

The target resource's policy `create?` takes precedence — if `UserPolicy.create?`
returns `false`, the creation link is hidden regardless of `can_create`.

---

## Has One

Shows the unfolded Show view of the associated record. Includes Attach/Detach buttons.

```ruby
field :admin, as: :has_one
```

### Has One Options

```ruby
field :admin,
  as: :has_one,
  searchable: true,
  attach_scope: -> { query.where(role: :admin) }
```

### Show on Edit Screens

```ruby
field :admin, as: :has_one, show_on: :edit
```

### Nested in Forms

Enable inline creation/editing within the parent form:

```ruby
field :author, as: :has_one, nested: true

# Or control which views:
field :author, as: :has_one, nested: { on: :new }
field :author, as: :has_one, nested: { on: :edit }
field :author, as: :has_one, nested: { on: :forms }
```

---

## Has Many

Renders a table of associated records below the resource fields on Show view.

```ruby
field :projects, as: :has_many
```

### Searchable Has Many

```ruby
field :links, as: :has_many, searchable: true
```

Requires `search` on the target resource:

```ruby
class Avo::Resources::CourseLink < Avo::BaseResource
  self.search = {
    query: -> {
      query.ransack(id_eq: q, link_cont: q, m: "or").result(distinct: false)
    }
  }
end
```

### Scoping Association Records

Filter which records display in the association table:

```ruby
class Avo::Resources::User < Avo::BaseResource
  def fields
    field :comments,
      as: :has_many,
      scope: -> { query.approved }
  end
end
```

With parent access:

```ruby
field :comments,
  as: :has_many,
  scope: -> { query.where(visible_to: parent.role) }
```

Starting with version 3.12, `resource` and `parent_resource` are also available.

### Attach Scope (Has Many)

Filter records in the **Attach modal** (not the listing):

```ruby
field :members,
  as: :has_many,
  attach_scope: -> { query.where.not(team_id: parent.id) }
```

**Important**: `attach_scope` only affects the Attach modal. Use `scope` or a
Pundit policy `Scope` to filter the association listing.

### Has Many Through

```ruby
field :members,
  as: :has_many,
  through: :memberships
```

With extra fields on the join table:

```ruby
field :patrons,
  as: :has_many,
  through: :patronships,
  attach_fields: -> {
    field :review, as: :text
  }
```

For polymorphic through associations, include a hidden type field:

```ruby
field :patrons,
  as: :has_many,
  through: :patronships,
  attach_fields: -> {
    field :review, as: :text
    field :patronship_type, as: :hidden, default: "TheType"
  }
```

### Search Query Scope

When the target resource has `search` configured, Avo scopes searches to the
association. Differentiate with `params[:via_association]`:

```ruby
self.search = {
  query: -> {
    if params[:via_association] == 'has_many'
      query.ransack(id_eq: q, m: "or").result(distinct: false).order(name: :asc)
    else
      query.ransack(id_eq: q, m: "or").result(distinct: false)
    end
  }
}
```

### Display Options

```ruby
field :comments,
  as: :has_many,
  name: "Discussion",
  description: "User-submitted comments",
  hide_search_input: true,
  hide_filter_button: true,
  discreet_pagination: true
```

| Option                | Default | Description                                     |
|-----------------------|---------|-------------------------------------------------|
| `name`                | auto    | Custom label (string or lambda)                 |
| `description`         | `nil`   | Text below the association name                 |
| `hide_search_input`   | `false` | Hide search input on association table          |
| `hide_filter_button`  | `false` | Hide filters button on association table        |
| `discreet_pagination` | `false` | Hide pagination when only one page              |
| `use_resource`        | `nil`   | Use a different Avo resource class              |
| `link_to_child_resource` | `false` | Use inherited STI resource on click          |

### Show on Edit Screens

```ruby
field :comments, as: :has_many, show_on: :edit
```

### Nested in Forms

```ruby
field :authors, as: :has_many, nested: true

field :authors, as: :has_many, nested: { on: :forms, limit: 5 }

field :authors, as: :has_many, nested: { on: [:new, :edit], limit: 2 }
```

The `limit` option hides the "Add" button when reached.

### Reloadable Associations

Add a reload icon to refresh the association's Turbo Frame:

```ruby
field :reviews, as: :has_many, reloadable: true

field :reviews, as: :has_many,
  reloadable: -> { current_user.is_admin? }
```

### For Attribute (Multiple Views of Same Association)

Display the same association multiple times with different scopes:

```ruby
field :reviews, as: :has_many

field :special_reviews,
  as: :has_many,
  for_attribute: :reviews,
  scope: -> { query.special_reviews }
```

---

## Has And Belongs To Many

Works similarly to Has Many:

```ruby
field :users, as: :has_and_belongs_to_many
```

Supports the same options as Has Many:

```ruby
field :users,
  as: :has_and_belongs_to_many,
  searchable: true,
  scope: -> { query.active },
  attach_scope: -> { query.where.not(team_id: parent.id) },
  name: "Team Members",
  description: "Active team members",
  hide_search_input: false,
  discreet_pagination: true
```

---

## Association Scopes

Two distinct scope mechanisms serve different purposes:

### `scope` — Filter the Listing

Controls which records appear in the association table:

```ruby
# Only show approved comments
field :comments, as: :has_many,
  scope: -> { query.approved }
```

Available in lambda: `query`, `parent`, `resource`, `parent_resource` (3.12+).

### `attach_scope` — Filter the Attach Modal

Controls which records appear in the Attach dropdown/search:

```ruby
# Only allow attaching non-admin users
field :members, as: :has_many,
  attach_scope: -> { query.where.not(role: :admin) }
```

Available in lambda: `query`, `parent`.

### Pundit Policy Scope on Associations

Policy scopes do NOT apply to association listings automatically.
Manually apply them via the `scope` option:

```ruby
field :comments, as: :has_many,
  scope: -> { Pundit.policy_scope(parent, query) }
```

---

## Association Authorization

Control button visibility on association panels through the parent resource's policy.
See [authorization.md](authorization.md) for full details.

### Quick Reference

```ruby
# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  # Controls "Attach comment" button (record = Post)
  def attach_comments? = user.admin?

  # Controls detach button per row (record = Comment)
  def detach_comments? = user.admin? || record.user_id == user.id

  # Controls entire association panel (record = Post)
  def view_comments? = true

  # Controls view button per row (record = Comment)
  def show_comments? = true

  # Controls edit button per row (record = Comment)
  def edit_comments? = user.admin? || record.user_id == user.id

  # Controls "Create comment" button (record = Post)
  def create_comments? = user.admin? || user.editor?

  # Controls delete button per row (record = Comment)
  def destroy_comments? = user.admin?

  # Controls Actions dropdown (record = Post)
  def act_on_comments? = user.admin?

  # Controls reorder buttons (record = Post)
  def reorder_comments? = user.admin?
end
```

Or use `PolicyHelpers` to auto-delegate:

```ruby
class PostPolicy < ApplicationPolicy
  inherit_association_from_policy :comments, CommentPolicy
end
```

---

## Records Ordering on Associations

Enable reordering within associations using `self.ordering` on the child resource:

```ruby
class Avo::Resources::MenuItem < Avo::BaseResource
  self.ordering = {
    visible_on: :association,
    display_inline: true,
    actions: {
      higher: -> { record.move_higher },
      lower: -> { record.move_lower },
      to_top: -> { record.move_to_top },
      to_bottom: -> { record.move_to_bottom },
    }
  }
end
```

### Drag and Drop

```ruby
self.ordering = {
  visible_on: :association,
  display_inline: true,
  drag_and_drop: true,
  actions: {
    higher: -> { record.move_higher },
    lower: -> { record.move_lower },
    to_top: -> { record.move_to_top },
    to_bottom: -> { record.move_to_bottom },
    insert_at: -> { record.insert_at position }
  }
}
```

With custom position attribute:

```ruby
self.ordering = {
  visible_on: %i[index association],
  position: -> { record.position_in_list },
  drag_and_drop: true,
  actions: {
    higher: -> { record.move_higher },
    lower: -> { record.move_lower },
    to_top: -> { record.move_to_top },
    to_bottom: -> { record.move_to_bottom },
    insert_at: -> { record.insert_at position }
  }
}
```

Authorize reordering via policy:

```ruby
class MenuItemPolicy < ApplicationPolicy
  def reorder? = edit?
end
```

`visible_on` accepts: `:index`, `:association`, or `[:index, :association]`.

---

## STI (Single Table Inheritance)

### Link to Child Resource

When a parent resource lists STI records, redirect clicks to the child resource:

```ruby
# On the parent resource
class Avo::Resources::Person < Avo::BaseResource
  self.link_to_child_resource = true
end
```

Per-association:

```ruby
field :peoples, as: :has_many, link_to_child_resource: true
```

The child resource must declare its `model_class`:

```ruby
class Avo::Resources::SuperUser < Avo::BaseResource
  self.model_class = "SuperUser"
end
```

---

## Common Options Reference

Options available on all association field types:

| Option         | Types           | Description                                    |
|----------------|-----------------|------------------------------------------------|
| `searchable`   | all             | Search input instead of dropdown               |
| `attach_scope` | all             | Filter records in Attach modal                 |
| `scope`        | has_many, habtm | Filter records in listing                      |
| `name`         | has_many, habtm | Custom display label                           |
| `description`  | has_many, habtm | Text below association name                    |
| `use_resource` | all             | Use a different Avo resource                   |
| `show_on`      | all             | Control view visibility (`:edit`, `:show`)      |
| `nested`       | has_one, has_many, habtm | Enable nested forms                 |
| `through`      | has_many        | Specify join model for has_many :through        |
| `attach_fields`| has_many        | Extra fields on the join table attach form      |
| `reloadable`   | has_many, habtm | Add reload icon for Turbo Frame                |
| `for_attribute`| has_many, habtm | Map field to a different association attribute  |
| `polymorphic_as` | belongs_to    | Polymorphic association key                    |
| `types`        | belongs_to      | Polymorphic type options                        |
| `allow_via_detaching` | belongs_to | Keep field enabled when visiting via parent |
| `can_create`   | belongs_to      | Show/hide inline creation link                 |
