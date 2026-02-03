# PRT BRI Scraping

- Data scraped from [here](https://app.powerbi.com/view?r=eyJrIjoiZDJiMDg1NTgtYzJlMS00NzYzLWEwYTUtMzc2NDg1ZmQxZGVlIiwidCI6ImU1M2ExOGFmLWJmOTgtNDg0My1hMmRkLWEwOTYyZDNlZjcyNSIsImMiOjJ9&pageName=ReportSectionec29f31e20b13357636f)
- Unsure how robust the HTTP requests are
    - Keys/IDs taken from a single session
    - May need user to regenerate them
    - Calls did not show any sign of timeout with 0.5 sleeps in between
- Graph and parse_data scripts made by Copilot
    - Missing years between 2020-2023
    - Data that is there seems correct
