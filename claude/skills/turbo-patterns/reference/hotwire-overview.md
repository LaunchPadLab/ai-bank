# Hotwire Overview

## What is Hotwire?

Hotwire = HTML Over The Wire — Build modern web apps without writing much JavaScript.

| Component | Purpose | Use Case |
|-----------|---------|----------|
| **Turbo Drive** | SPA-like navigation | Automatic, no code needed |
| **Turbo Frames** | Partial page updates | Inline editing, tabbed content |
| **Turbo Streams** | Real-time DOM updates | Live updates, flash messages |
| **Stimulus** | JavaScript sprinkles | Toggles, forms, interactions |

## When to Use Each Pattern

| Scenario | Pattern | Why |
|----------|---------|-----|
| Inline edit | Turbo Frame | Scoped replacement |
| Form submission | Turbo Stream | Multiple updates |
| Real-time feed | Turbo Stream + ActionCable | Push updates |
| Toggle visibility | Stimulus | No server needed |
| Form validation | Stimulus | Client-side feedback |
| Infinite scroll | Turbo Frame + lazy loading | Paginated content |
| Modal dialogs | Turbo Frame | Load on demand |
| Flash messages | Turbo Stream | Append/update |

## Workflow Checklist

```
Hotwire Implementation:
- [ ] Identify update scope (full page vs partial)
- [ ] Choose pattern (Frame vs Stream vs Stimulus)
- [ ] Implement server response
- [ ] Add client-side markup
- [ ] Test with and without JavaScript
- [ ] Write system spec
```

## Testing Hotwire

### System Tests

```ruby
# test/system/posts_test.rb
require "test_helper"

class PostsSystemTest < ActionDispatch::SystemTestCase
  driven_by(:selenium, using: :headless_chrome)

  test "updates post inline with Turbo Frame" do
    post = posts(:one)

    visit posts_path
    within("#post_#{post.id}") do
      click_link "Edit"
      fill_in "Title", with: "Updated"
      click_button "Save"
    end

    assert_text "Updated"
    assert_no_text "Original"
  end

  test "adds comment with Turbo Stream" do
    post = posts(:one)

    visit post_path(post)
    fill_in "Comment", with: "Great post!"
    click_button "Add Comment"

    within("#comments") do
      assert_text "Great post!"
    end
  end
end
```

### Request Tests for Turbo Stream

```ruby
# test/requests/posts_test.rb
require "test_helper"

class PostsTurboStreamTest < ActionDispatch::IntegrationTest
  test "returns turbo stream response" do
    post posts_path,
         params: { post: { title: "Test" } },
         headers: { "Accept" => "text/vnd.turbo-stream.html" }

    assert_equal "text/vnd.turbo-stream.html", response.media_type
    assert_includes response.body, "turbo-stream"
  end
end
```

## Common Patterns

### Inline Editing with Frame

```erb
<%# _post.html.erb %>
<%= turbo_frame_tag dom_id(post) do %>
  <article>
    <h2><%= post.title %></h2>
    <%= link_to "Edit", edit_post_path(post) %>
  </article>
<% end %>

<%# edit.html.erb %>
<%= turbo_frame_tag dom_id(@post) do %>
  <%= form_with model: @post do |f| %>
    <%= f.text_field :title %>
    <%= f.submit "Save" %>
    <%= link_to "Cancel", @post %>
  <% end %>
<% end %>
```

### Flash Messages with Stream

```ruby
# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  after_action :flash_to_turbo_stream, if: -> { request.format.turbo_stream? }

  private

  def flash_to_turbo_stream
    flash.each do |type, message|
      flash.now[type] = message
    end
  end
end
```

### Lazy Loading Frame

```erb
<%= turbo_frame_tag "comments", src: post_comments_path(@post), loading: :lazy do %>
  <p>Loading comments...</p>
<% end %>
```

## Debugging Tips

1. **Frame not updating?** Check frame IDs match exactly
2. **Stream not working?** Verify `Accept` header includes turbo-stream
3. **Stimulus not firing?** Check controller name matches file name
4. **Events not working?** Use `data-action="event->controller#method"`
