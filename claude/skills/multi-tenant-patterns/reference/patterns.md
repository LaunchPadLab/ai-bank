# Multi-Tenant Patterns — Detailed Code Examples

Complete implementation code for all multi-tenancy patterns. See [SKILL.md](../SKILL.md) for philosophy, pattern summaries, and guidelines.

## Pattern 1: Account Model and Memberships

Build the foundation for multi-tenancy with Account and Membership models.

```ruby
# app/models/account.rb
class Account < ApplicationRecord
  has_many :memberships, dependent: :destroy
  has_many :users, through: :memberships

  # All account resources
  has_many :boards, dependent: :destroy
  has_many :cards, dependent: :destroy
  has_many :comments, dependent: :destroy
  has_many :activities, dependent: :destroy

  validates :name, presence: true, length: { maximum: 100 }

  def member?(user)
    users.exists?(user.id)
  end

  def add_member(user, role: :member)
    memberships.find_or_create_by!(user: user) do |membership|
      membership.role = role
    end
  end

  def remove_member(user)
    memberships.find_by(user: user)&.destroy
  end

  def owner
    memberships.owner.first&.user
  end
end

# app/models/membership.rb
class Membership < ApplicationRecord
  belongs_to :user
  belongs_to :account

  enum :role, { member: 0, admin: 1, owner: 2 }

  validates :user_id, uniqueness: { scope: :account_id }
  validates :role, presence: true

  scope :active, -> { where(active: true) }
  scope :for_account, ->(account) { where(account: account) }
  scope :for_user, ->(user) { where(user: user) }
end

# app/models/user.rb
class User < ApplicationRecord
  has_many :memberships, dependent: :destroy
  has_many :accounts, through: :memberships

  validates :email, presence: true, uniqueness: true
  validates :name, presence: true

  def member_of?(account)
    accounts.exists?(account.id)
  end

  def role_in(account)
    memberships.find_by(account: account)&.role
  end

  def admin_of?(account)
    memberships.find_by(account: account)&.admin? ||
    memberships.find_by(account: account)&.owner?
  end

  def owner_of?(account)
    memberships.find_by(account: account)&.owner?
  end
end

# db/migrate/xxx_create_accounts.rb
class CreateAccounts < ActiveRecord::Migration[8.0]
  def change
    create_table :accounts, id: :uuid do |t|
      t.string :name, null: false
      t.string :slug

      t.timestamps
    end

    add_index :accounts, :slug, unique: true
  end
end

# db/migrate/xxx_create_memberships.rb
class CreateMemberships < ActiveRecord::Migration[8.0]
  def change
    create_table :memberships, id: :uuid do |t|
      t.references :user, null: false, type: :uuid
      t.references :account, null: false, type: :uuid
      t.integer :role, null: false, default: 0
      t.boolean :active, null: false, default: true

      t.timestamps
    end

    add_index :memberships, [:user_id, :account_id], unique: true
    add_index :memberships, [:account_id, :role]
    add_index :memberships, [:user_id, :active]
  end
end
```

## Pattern 2: Current Attributes for Request Context

Use Current to store account and user context per-request.

```ruby
# app/models/current.rb
class Current < ActiveSupport::CurrentAttributes
  attribute :user, :account, :membership

  delegate :admin?, :owner?, to: :membership, allow_nil: true, prefix: true

  def member?
    membership.present?
  end

  def can_edit?(resource)
    return false unless member?
    return true if membership_admin? || membership_owner?

    resource.respond_to?(:creator) && resource.creator == user
  end

  def can_destroy?(resource)
    membership_admin? || membership_owner?
  end

  resets do
    Time.zone = nil
  end
end

# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  before_action :authenticate_user!
  before_action :set_current_account
  before_action :set_current_membership
  before_action :ensure_account_member

  private

  def authenticate_user!
    redirect_to sign_in_path unless current_user
  end

  def current_user
    Current.user ||= find_user_from_session
  end
  helper_method :current_user

  def set_current_account
    if params[:account_id]
      Current.account = current_user.accounts.find(params[:account_id])
    end
  rescue ActiveRecord::RecordNotFound
    redirect_to accounts_path, alert: "Account not found or access denied"
  end

  def set_current_membership
    if Current.account
      Current.membership = current_user.memberships.find_by(account: Current.account)
    end
  end

  def ensure_account_member
    return unless Current.account

    unless Current.member?
      redirect_to accounts_path, alert: "You don't have access to this account"
    end
  end

  def require_admin!
    unless Current.membership_admin?
      redirect_to account_path(Current.account), alert: "Admin access required"
    end
  end

  def require_owner!
    unless Current.membership_owner?
      redirect_to account_path(Current.account), alert: "Owner access required"
    end
  end
end
```

## Pattern 3: URL-Based Routing

Structure routes with account_id in the path.

```ruby
# config/routes.rb
Rails.application.routes.draw do
  # Authentication (no account context)
  resource :session, only: [:new, :create, :destroy]
  resources :magic_links, only: [:create, :show], param: :token

  # Account selection (no specific account)
  resources :accounts, only: [:index, :new, :create]

  # All routes within account context
  scope "/:account_id" do
    resource :account, only: [:show, :edit, :update, :destroy]
    resources :memberships, only: [:index, :create, :destroy]

    resources :boards do
      resources :cards do
        resources :comments, only: [:create, :destroy]
        resource :closure, only: [:create, :destroy]
      end

      resources :columns, only: [:create, :update, :destroy]
      resource :archive, only: [:create, :destroy]
    end

    resources :activities, only: [:index]
    resources :settings, only: [:index, :update]

    root "dashboards#show", as: :account_root
  end

  root "accounts#index"
end

# Alternative: Use a constraint for cleaner URLs
# scope "/a/:account_id", as: :account do
#   resources :boards
# end

# Or use account slug: /acme/boards
# scope "/:account_slug", as: :account, constraints: { account_slug: /[a-z0-9-]+/ } do
#   resources :boards
# end
```

**Path helpers usage:**
```ruby
account_boards_path(@account)          # => /123/boards
account_board_path(@account, @board)   # => /123/boards/456

# In views
<%= link_to "Boards", account_boards_path(Current.account) %>
<%= link_to @board.name, account_board_path(Current.account, @board) %>
```

## Pattern 4: Account-Scoped Models

Add account_id to every model and scope all queries through Current.account.

```ruby
# app/models/board.rb
class Board < ApplicationRecord
  belongs_to :account
  belongs_to :creator, class_name: "User"

  has_many :cards, dependent: :destroy
  has_many :columns, dependent: :destroy
  has_many :activities, dependent: :destroy

  validates :account_id, presence: true
  validates :name, presence: true, length: { maximum: 100 }

  scope :for_account, ->(account) { where(account: account) }
  scope :recent, -> { order(created_at: :desc) }

  before_validation :set_account, on: :create

  private

  def set_account
    self.account ||= Current.account
  end
end

# app/models/card.rb
class Card < ApplicationRecord
  belongs_to :account
  belongs_to :board
  belongs_to :column
  belongs_to :creator, class_name: "User"

  has_many :comments, dependent: :destroy
  has_many :assignments, dependent: :destroy
  has_many :assigned_users, through: :assignments, source: :user

  validates :account_id, presence: true
  validates :title, presence: true, length: { maximum: 200 }

  validate :account_matches_board

  before_validation :set_account, on: :create

  private

  def set_account
    self.account ||= board&.account || Current.account
  end

  def account_matches_board
    if board && account_id != board.account_id
      errors.add(:account_id, "must match board's account")
    end
  end
end

# app/models/comment.rb
class Comment < ApplicationRecord
  belongs_to :account
  belongs_to :card
  belongs_to :creator, class_name: "User"

  validates :account_id, presence: true
  validates :body, presence: true

  before_validation :set_account, on: :create

  private

  def set_account
    self.account ||= card&.account || Current.account
  end
end

# app/models/concerns/account_scoped.rb
module AccountScoped
  extend ActiveSupport::Concern

  included do
    belongs_to :account
    validates :account_id, presence: true

    before_validation :set_account_from_current, on: :create

    scope :for_account, ->(account) { where(account: account) }
  end

  private

  def set_account_from_current
    self.account ||= Current.account
  end
end

# Usage
class Board < ApplicationRecord
  include AccountScoped
  # ... rest of model
end
```

## Pattern 5: Account-Scoped Controllers

Always scope queries through Current.account.

```ruby
# app/controllers/boards_controller.rb
class BoardsController < ApplicationController
  before_action :set_board, only: [:show, :edit, :update, :destroy]

  def index
    @boards = Current.account.boards
      .includes(:creator)
      .recent
  end

  def show
  end

  def new
    @board = Current.account.boards.build
  end

  def create
    @board = Current.account.boards.build(board_params)
    @board.creator = Current.user

    if @board.save
      redirect_to account_board_path(Current.account, @board), notice: "Board created"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def update
    if @board.update(board_params)
      redirect_to account_board_path(Current.account, @board), notice: "Board updated"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @board.destroy
    redirect_to account_boards_path(Current.account), notice: "Board deleted"
  end

  private

  def set_board
    @board = Current.account.boards.find(params[:id])
  end

  def board_params
    params.require(:board).permit(:name, :description)
  end
end

# app/controllers/cards_controller.rb
class CardsController < ApplicationController
  before_action :set_board
  before_action :set_card, only: [:show, :edit, :update, :destroy]

  def index
    @cards = @board.cards.includes(:creator, :column)
  end

  def show
  end

  def create
    @card = @board.cards.build(card_params)
    @card.creator = Current.user
    @card.account = Current.account

    if @card.save
      redirect_to account_board_card_path(Current.account, @board, @card)
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def set_board
    @board = Current.account.boards.find(params[:board_id])
  end

  def set_card
    @card = @board.cards.find(params[:id])
  end

  def card_params
    params.require(:card).permit(:title, :description, :column_id)
  end
end

# app/controllers/concerns/account_scoped_controller.rb
module AccountScopedController
  extend ActiveSupport::Concern

  private

  def scope_to_account(relation)
    relation.where(account: Current.account)
  end

  def build_for_account(relation, attributes = {})
    relation.build(attributes.merge(account: Current.account))
  end
end
```

## Pattern 6: Account Switching and Selection

Let users switch between accounts they belong to.

```ruby
# app/controllers/accounts_controller.rb
class AccountsController < ApplicationController
  skip_before_action :set_current_account, only: [:index, :new, :create]
  skip_before_action :ensure_account_member, only: [:index, :new, :create]

  def index
    @accounts = current_user.accounts.order(:name)

    if @accounts.size == 1
      redirect_to account_root_path(@accounts.first)
    elsif last_account = find_last_accessed_account
      redirect_to account_root_path(last_account)
    end
  end

  def show
    redirect_to account_root_path(Current.account)
  end

  def new
    @account = Account.new
  end

  def create
    @account = Account.new(account_params)

    if @account.save
      @account.add_member(current_user, role: :owner)

      redirect_to account_root_path(@account), notice: "Account created"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    require_admin!
  end

  def update
    require_admin!

    if Current.account.update(account_params)
      redirect_to account_path(Current.account), notice: "Account updated"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    require_owner!

    Current.account.destroy
    redirect_to accounts_path, notice: "Account deleted"
  end

  private

  def account_params
    params.require(:account).permit(:name, :slug)
  end

  def find_last_accessed_account
    account_id = session[:last_account_id]
    current_user.accounts.find_by(id: account_id) if account_id
  end
end

# app/controllers/application_controller.rb (addition)
class ApplicationController < ActionController::Base
  after_action :store_last_accessed_account

  private

  def store_last_accessed_account
    if Current.account
      session[:last_account_id] = Current.account.id
    end
  end
end
```

**Account switcher in views:**
```erb
<%# app/views/layouts/application.html.erb %>
<nav>
  <% if Current.account %>
    <div class="account-switcher">
      <%= link_to Current.account.name, account_path(Current.account) %>

      <div class="dropdown">
        <% current_user.accounts.each do |account| %>
          <% if account != Current.account %>
            <%= link_to account.name, account_root_path(account) %>
          <% end %>
        <% end %>

        <%= link_to "Create Account", new_account_path %>
      </div>
    </div>
  <% end %>
</nav>

<%# app/views/accounts/index.html.erb %>
<h1>Your Accounts</h1>

<div class="accounts">
  <% @accounts.each do |account| %>
    <div class="account-card">
      <h2><%= link_to account.name, account_root_path(account) %></h2>

      <p class="role">
        <%= current_user.role_in(account).to_s.titleize %>
      </p>
    </div>
  <% end %>
</div>

<%= link_to "Create New Account", new_account_path, class: "button" %>
```

## Pattern 7: Membership Management

Invite and manage account members.

```ruby
# app/controllers/memberships_controller.rb
class MembershipsController < ApplicationController
  before_action :require_admin!, except: [:index]

  def index
    @memberships = Current.account.memberships
      .includes(:user)
      .order(created_at: :desc)
  end

  def create
    user = User.find_by!(email: membership_params[:email])

    @membership = Current.account.add_member(
      user,
      role: membership_params[:role] || :member
    )

    MembershipMailer.invitation(@membership).deliver_later

    redirect_to account_memberships_path(Current.account),
                notice: "#{user.name} added to account"
  rescue ActiveRecord::RecordNotFound
    redirect_to account_memberships_path(Current.account),
                alert: "User not found. They need to sign up first."
  end

  def destroy
    @membership = Current.account.memberships.find(params[:id])

    if @membership.user == current_user && @membership.owner?
      redirect_to account_memberships_path(Current.account),
                  alert: "Owner cannot remove themselves"
      return
    end

    @membership.destroy

    redirect_to account_memberships_path(Current.account),
                notice: "Member removed"
  end

  private

  def membership_params
    params.require(:membership).permit(:email, :role)
  end
end

# app/mailers/membership_mailer.rb
class MembershipMailer < ApplicationMailer
  def invitation(membership)
    @membership = membership
    @account = membership.account
    @user = membership.user

    mail(
      to: @user.email,
      subject: "You've been invited to #{@account.name}"
    )
  end
end
```

**Membership views:**
```erb
<%# app/views/memberships/index.html.erb %>
<h1>Members of <%= Current.account.name %></h1>

<% if Current.membership_admin? %>
  <%= render "memberships/invite_form" %>
<% end %>

<table class="memberships">
  <thead>
    <tr>
      <th>Member</th>
      <th>Email</th>
      <th>Role</th>
      <th>Joined</th>
      <th></th>
    </tr>
  </thead>

  <tbody>
    <% @memberships.each do |membership| %>
      <tr>
        <td><%= membership.user.name %></td>
        <td><%= membership.user.email %></td>
        <td><%= membership.role.titleize %></td>
        <td><%= membership.created_at.to_date %></td>
        <td>
          <% if Current.membership_admin? && membership != Current.membership %>
            <%= button_to "Remove",
                account_membership_path(Current.account, membership),
                method: :delete,
                data: { confirm: "Remove #{membership.user.name}?" } %>
          <% end %>
        </td>
      </tr>
    <% end %>
  </tbody>
</table>

<%# app/views/memberships/_invite_form.html.erb %>
<%= form_with url: account_memberships_path(Current.account) do |f| %>
  <div class="field">
    <%= f.label :email, "Email address" %>
    <%= f.email_field :email, required: true %>
  </div>

  <div class="field">
    <%= f.label :role %>
    <%= f.select :role,
        Membership.roles.keys.map { |r| [r.titleize, r] },
        selected: "member" %>
  </div>

  <%= f.submit "Invite Member" %>
<% end %>
```

## Pattern 8: Data Isolation and Security

Ensure complete data isolation between accounts.

```ruby
# app/models/concerns/account_isolation.rb
module AccountIsolation
  extend ActiveSupport::Concern

  included do
    validate :validate_account_consistency, on: :create
  end

  private

  def validate_account_consistency
    self.class.reflect_on_all_associations(:belongs_to).each do |assoc|
      next if assoc.name == :account
      next unless assoc.options[:class_name]

      related = send(assoc.name)
      next unless related

      if related.respond_to?(:account_id) && related.account_id != account_id
        errors.add(assoc.name, "must belong to the same account")
      end
    end
  end
end

# Usage
class Card < ApplicationRecord
  include AccountScoped
  include AccountIsolation

  belongs_to :board
  belongs_to :column

  # Automatically validates board.account_id == card.account_id
  # and column.account_id == card.account_id
end
```

**Controller security:**
```ruby
# app/controllers/concerns/account_security.rb
module AccountSecurity
  extend ActiveSupport::Concern

  included do
    rescue_from ActiveRecord::RecordNotFound, with: :record_not_found
  end

  private

  def record_not_found
    redirect_to account_root_path(Current.account),
                alert: "Resource not found"
  end

  def ensure_same_account(*resources)
    resources.each do |resource|
      if resource.respond_to?(:account_id) && resource.account_id != Current.account.id
        raise ActiveRecord::RecordNotFound
      end
    end
  end
end

# app/controllers/cards_controller.rb
class CardsController < ApplicationController
  include AccountSecurity

  def show
    @board = Current.account.boards.find(params[:board_id])
    @card = @board.cards.find(params[:id])

    ensure_same_account(@board, @card)
  end
end
```

## Pattern 9: Cross-Account References (When Needed)

Handle rare cases where resources reference across accounts.

```ruby
# app/models/integration.rb
class Integration < ApplicationRecord
  has_many :integration_accounts, dependent: :destroy
  has_many :accounts, through: :integration_accounts

  def authorized_for?(account)
    accounts.exists?(account.id)
  end
end

# app/models/integration_account.rb
class IntegrationAccount < ApplicationRecord
  belongs_to :integration
  belongs_to :account

  validates :account_id, uniqueness: { scope: :integration_id }
end

# app/models/webhook_endpoint.rb
class WebhookEndpoint < ApplicationRecord
  belongs_to :account

  validates :url, presence: true
  validates :account_id, presence: true

  def deliver(payload)
    HTTP.post(url, json: payload)
  end
end
```

## Pattern 10: Account Migrations

Add account_id to existing tables safely.

```ruby
# db/migrate/xxx_add_account_to_cards.rb
class AddAccountToCards < ActiveRecord::Migration[8.0]
  def change
    add_reference :cards, :account, type: :uuid, null: true

    reversible do |dir|
      dir.up do
        execute <<-SQL
          UPDATE cards
          SET account_id = boards.account_id
          FROM boards
          WHERE cards.board_id = boards.id
        SQL

        change_column_null :cards, :account_id, false
      end
    end

    add_index :cards, [:account_id, :created_at]
    add_index :cards, [:account_id, :board_id]
  end
end

# db/migrate/xxx_add_account_to_multiple_tables.rb
class AddAccountToMultipleTables < ActiveRecord::Migration[8.0]
  def change
    [:cards, :comments, :activities, :attachments].each do |table|
      add_reference table, :account, type: :uuid, null: true
      add_index table, [:account_id, :created_at]
    end

    reversible do |dir|
      dir.up do
        backfill_accounts

        [:cards, :comments, :activities, :attachments].each do |table|
          change_column_null table, :account_id, false
        end
      end
    end
  end

  def backfill_accounts
    execute <<-SQL
      UPDATE cards
      SET account_id = boards.account_id
      FROM boards
      WHERE cards.board_id = boards.id
    SQL

    execute <<-SQL
      UPDATE comments
      SET account_id = cards.account_id
      FROM cards
      WHERE comments.card_id = cards.id
    SQL

    execute <<-SQL
      UPDATE activities
      SET account_id = cards.account_id
      FROM cards
      WHERE activities.subject_type = 'Card'
      AND activities.subject_id = cards.id
    SQL
  end
end
```

## Testing Patterns

Test multi-tenancy isolation and account scoping.

```ruby
# test/models/board_test.rb
require "test_helper"

class BoardTest < ActiveSupport::TestCase
  test "sets account from Current on create" do
    account = accounts(:acme)
    Current.account = account

    board = Board.create!(name: "Test Board", creator: users(:alice))

    assert_equal account, board.account
  end

  test "validates presence of account_id" do
    board = Board.new(name: "Test", creator: users(:alice))

    assert_not board.valid?
    assert board.errors.added?(:account_id, :blank)
  end

  test "scopes cards to same account" do
    board = boards(:design)
    card = cards(:one)

    assert_equal board.account_id, card.account_id
  end
end

# test/models/card_test.rb
require "test_helper"

class CardTest < ActiveSupport::TestCase
  test "validates account matches board account" do
    card = Card.new(
      title: "Test",
      board: boards(:design),
      account: accounts(:globex), # Different account!
      creator: users(:alice)
    )

    assert_not card.valid?
    assert_includes card.errors[:account_id], "must match board's account"
  end

  test "sets account from board" do
    board = boards(:design)
    card = Card.new(title: "Test", board: board, creator: users(:alice))

    assert_equal board.account, card.account
  end
end

# test/controllers/boards_controller_test.rb
require "test_helper"

class BoardsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account = accounts(:acme)
    @user = users(:alice)
    sign_in_as @user
  end

  test "index scopes to current account" do
    other_account = accounts(:globex)
    other_board = Board.create!(
      name: "Other Board",
      account: other_account,
      creator: users(:bob)
    )

    get account_boards_path(@account)

    assert_response :success
    assert_select "h2", text: boards(:design).name
    assert_select "h2", text: other_board.name, count: 0
  end

  test "show finds board only in current account" do
    other_account = accounts(:globex)
    other_board = Board.create!(
      name: "Other Board",
      account: other_account,
      creator: users(:bob)
    )

    assert_raises ActiveRecord::RecordNotFound do
      get account_board_path(@account, other_board)
    end
  end

  test "create associates board with current account" do
    assert_difference "Board.count" do
      post account_boards_path(@account),
           params: { board: { name: "New Board" } }
    end

    board = Board.last
    assert_equal @account, board.account
    assert_equal @user, board.creator
  end
end

# test/controllers/cards_controller_test.rb
require "test_helper"

class CardsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @account = accounts(:acme)
    @board = boards(:design)
    @user = users(:alice)
    sign_in_as @user
  end

  test "show finds card only in current account and board" do
    other_account = accounts(:globex)
    other_board = Board.create!(
      name: "Other Board",
      account: other_account,
      creator: users(:bob)
    )
    other_card = Card.create!(
      title: "Other Card",
      board: other_board,
      account: other_account,
      creator: users(:bob)
    )

    assert_raises ActiveRecord::RecordNotFound do
      get account_board_card_path(@account, @board, other_card)
    end
  end

  test "create sets account explicitly" do
    assert_difference "Card.count" do
      post account_board_cards_path(@account, @board),
           params: {
             card: {
               title: "New Card",
               column_id: columns(:todo).id
             }
           }
    end

    card = Card.last
    assert_equal @account, card.account
    assert_equal @board, card.board
  end
end

# test/system/account_switching_test.rb
require "application_system_test_case"

class AccountSwitchingTest < ApplicationSystemTestCase
  test "switches between accounts" do
    user = users(:alice)
    account1 = accounts(:acme)
    account2 = accounts(:globex)

    account1.add_member(user)
    account2.add_member(user)

    sign_in_as user

    visit accounts_path
    click_on account1.name

    assert_current_path account_root_path(account1)
    assert_text account1.name

    click_on account1.name # Open switcher
    click_on account2.name

    assert_current_path account_root_path(account2)
    assert_text account2.name
  end
end
```
