@bdd @smoke
Feature: Agents catalog UI
  As a Matrixly visitor
  I want a consistent agent catalog
  So that I can deploy marketplace agents confidently

  Scenario: Catalog page loads with deploy actions
    Given I open the "agents" page
    Then the page title should contain "Agents"
    And I should see at least 4 "Deploy Now" buttons
    And the site should link to Admin

  Scenario: Shipping Assistant card structure
    Given I open the "agents" page
    Then the "Shipping Assistant" card should show a "User guide" link
    And the "Shipping Assistant" card footer should end with "Deploy Now"
