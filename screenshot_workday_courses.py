#!/usr/bin/env python3
"""
Screenshot Computer Science courses from Workday for Spring 2026.
Requires: pip install playwright
Then run: playwright install chromium
"""

from playwright.sync_api import sync_playwright
import time


def screenshot_courses(page, subject_name, output_filename):
    """Screenshot courses for a given subject."""
    print(f"Searching for {subject_name} courses...")

    # Click on the Subject search textbox
    subject_search = page.get_by_role("textbox", name="Search").first
    subject_search.click()

    # Type the subject name
    subject_search.fill(subject_name)

    # Press Enter to search
    page.keyboard.press("Enter")

    # Wait for results to load
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Additional wait for dynamic content

    # Scroll to bottom to ensure all courses load
    page.evaluate("() => { window.scrollTo(0, document.body.scrollHeight); }")
    time.sleep(1)

    # Run JavaScript to make compact list
    page.evaluate("""() => {
        document.querySelectorAll('[aria-label="Search Results"] li[data-automation-id="compositeContainer"]').forEach(x => {
            // hide if text content contains "waitlist" or "closed"
            if (x.textContent.toLowerCase().includes('waitlist') || x.textContent.toLowerCase().includes('closed')) {
                x.style.display = 'none';
            } else {
                // remove padding
                x.style.padding = '0 0 0 10px';
                x.style.margin = '0';
            }

            document.querySelectorAll('[title="Section Details"]').forEach(y => { y.style.display = 'none'; });

            x.querySelectorAll('[data-automation-id="compositeSubHeaderOne"], [data-automation-id="compositeDetailPreview"]').forEach(y => {
                y.style.display = 'inline';
            });
        });
    }""")

    # Scroll back to top
    page.evaluate("() => { window.scrollTo(0, 0); }")
    time.sleep(1)

    # Take screenshot of just the Search Results region
    search_results = page.get_by_role("region", name="Search Results")
    search_results.screenshot(path=output_filename)
    print(f"Screenshot saved to {output_filename}")

    # Clear the search when we're done
    clear_button = page.get_by_role("button", name="Clear All")
    clear_button.click()
    time.sleep(1)


def main():
    with sync_playwright() as p:
        # Launch browser
        # Use the system-installed Chrome rather than Playwright's bundled Chromium
        # (alternatively use executable_path="/path/to/chrome" if preferred)
        browser = p.chromium.launch(headless=False, channel="chrome")
        page = browser.new_page()

        # Navigate to Workday
        print("Navigating to workday.calvin.edu...")
        page.goto("https://workday.calvin.edu")

        # Wait for login
        print("\n*** Please log in to Workday ***")
        print("Press Enter in this terminal after you've logged in...")
        input()

        # Search for Find Course Sections
        print("Searching for Find Course Sections report...")
        search_box = page.get_by_role("combobox", name="Search Workday")
        search_box.click()
        search_box.fill("Find Course Sections")
        # await page.getByRole('option', { name: 'Find Course Sections Report' }).click();
        time.sleep(1)  # Wait for dropdown to populate
        page.get_by_role("option", name="Find Course Sections Report").click()
        time.sleep(2)  # Wait for navigation

        # Wait for report dialog to open
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Fill in the search criteria
        print("Filling in search criteria...")

        # Start Date within
        start_date_field = page.get_by_role("textbox", name="Start Date within")
        start_date_field.click()
        start_date_field.fill("2026 Spring")
        page.keyboard.press("Enter")
        time.sleep(1)

        # Select the "2026 Spring" option (not Spring 1, Spring A, etc.)
        # The first option should be selected by default, click it
        page.keyboard.press("Enter")
        time.sleep(1)

        # Academic Level - click and select Undergraduate
        academic_level_field = page.get_by_role("textbox", name="Academic Level")
        academic_level_field.click()
        time.sleep(1)

        # Click the Undergraduate checkbox
        # Prefer ARIA role 'checkbox' but fall back to an option/listitem if not present
        undergraduate_checkbox = page.get_by_role("checkbox", name="Undergraduate")
        if undergraduate_checkbox.count() == 0:
            undergraduate_checkbox = page.get_by_role("option", name="Undergraduate").first
        undergraduate_checkbox.click()
        time.sleep(1)

        # Click OK to run the report
        print("Running report...")
        ok_button = page.get_by_role("button", name="OK")
        ok_button.click()
        ok_button.click()  # May need two clicks if first closes dropdown

        # Wait for results to load
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Now screenshot each subject
        subjects = [
            ("Computer Science", "cs-sections-spring-2026.png"),
            ("Mathematics", "math-sections-spring-2026.png"),
            ("Data Science", "data-science-sections-spring-2026.png"),
            ("Statistics", "statistics-sections-spring-2026.png"),
            ("Information Systems", "is-sections-spring-2026.png"),
        ]

        for subject_name, filename in subjects:
            screenshot_courses(page, subject_name, filename)
            time.sleep(2)  # Brief pause between subjects

        print("\nAll screenshots complete!")
        browser.close()


if __name__ == "__main__":
    main()
