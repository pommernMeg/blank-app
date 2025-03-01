import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from utils.sqlite_utils import connect_to_database
import tempfile
from datetime import datetime
from matplotlib.dates import DateFormatter

# Helper function to create a metric circle with text below
def create_metric_circle(value, title, color):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    circle = plt.Circle((0, 0), 0.8, color=color, ec="black", lw=1.5)
    ax.add_artist(circle)
    ax.text(0, 0, f"{value:.1f}", ha="center", va="center", fontsize=16, fontweight="bold", color="white")
    ax.text(0, -1.2, title, ha="center", va="center", fontsize=10, fontweight="bold", color="black")
    ax.axis("off")  # Remove axes for a cleaner look
    return fig

def create_books_read_summary(conn):
    """Fetch and display a summary of books read."""
    query = """
            SELECT 
                date(datetime(psd.start_time, 'unixepoch', '0 seconds')) AS reading_date,
                SUM(psd.duration) / 60.0 AS minutes_read
            FROM page_stat_data psd
            WHERE date(datetime(psd.start_time, 'unixepoch', '0 seconds')) >= date('now', '-30 days', '0 seconds') and psd.id_book NOT IN (1, 3 , 10)
            GROUP BY reading_date
            ORDER BY reading_date;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()

    # Create DataFrame
    df_books = pd.DataFrame(data, columns=["Book Title", "Total Pages Read", "Total Time Spent"])
    
    # Add total time in different units for inspection
    df_books["Total Time (raw units)"] = df_books["Total Time Spent"]
    df_books["Total Time (minutes)"] = df_books["Total Time Spent"].apply(lambda x: f"{x // 60}:{x % 60:02d}")  # Assuming milliseconds
    df_books["Total Time (hours)"] = df_books["Total Time Spent"].apply(lambda x: f"{x // 3600}:{(x % 3600) // 60:02d}")  # Assuming milliseconds
    
    # Calculate average reading speed (pages/hour)
    df_books["Average Reading Speed (pages/hour)"] = ((df_books['Total Pages Read'] * 3600) / df_books["Total Time (raw units)"].round(1)).round(2)

    st.write("### Books Read Summary")
    st.dataframe(df_books[[
        "Book Title", 
        "Total Pages Read", 
        "Total Time (raw units)", 
        "Total Time (minutes)", 
        "Total Time (hours)", 
        "Average Reading Speed (pages/hour)"
    ]])

    return df_books



def create_year_in_review_summary(conn):
    """Display year-in-review metrics and statistics."""
    year = datetime.now().year
    query = f"""
        SELECT 
            count(DISTINCT(date(datetime(psd.start_time, 'unixepoch', 'localtime')))) AS unique_days_reading,
			COUNT(DISTINCT b.id) AS books_completed,
			SUM(DISTINCT(b.total_read_time)) / (3600) AS total_hours_reading,
            sum(distinct( b.total_read_pages)) AS total_pages_read
        FROM page_stat_data psd
        JOIN book b ON psd.id_book = b.id
        WHERE strftime('%Y', datetime(psd.start_time, 'unixepoch', 'localtime')) = '{year}' and
        b.title NOT IN ('KOReader Quickstart Guide', 'Necroscope 003: Blutmesse') and b.id != 10
		ORDER by unique_days_reading
    """
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchone()

    unique_days_reading, books_completed, total_hours_reading, total_pages_read = results
    avg_time_per_day = total_hours_reading / unique_days_reading if unique_days_reading else 0
    avg_pages_per_day = total_pages_read / unique_days_reading if unique_days_reading else 0
    avg_reading_speed = total_pages_read / total_hours_reading if total_hours_reading else 0
    avg_days_to_complete_book = unique_days_reading / books_completed if books_completed else 0

    st.write("### Year in Review Metrics")
    col1, col2 = st.columns(2)

    with col1:
        fig = create_metric_circle(avg_time_per_day, "Avg Time Per Day (mins)", "skyblue")
        st.pyplot(fig)

    with col2:
        fig = create_metric_circle(avg_pages_per_day, "Avg Pages Per Day", "coral")
        st.pyplot(fig)

    col3, col4 = st.columns(2)

    with col3:
        fig = create_metric_circle(avg_reading_speed, "Avg Reading Speed (pages/hr)", "limegreen")
        st.pyplot(fig)

    with col4:
        fig = create_metric_circle(avg_days_to_complete_book, "Avg Days to Complete a Book", "gold")
        st.pyplot(fig)

    fig, ax = plt.subplots(figsize=(2.5, 2.5))
    circle = plt.Circle((0, 0), 0.6, color="orchid", ec="black", lw=1.2)
    ax.add_artist(circle)
    ax.text(0, 0, f"{books_completed}", ha="center", va="center", fontsize=14, fontweight="bold", color="white")
    ax.text(0, -0.9, "Books Completed", ha="center", va="center", fontsize=9, fontweight="bold", color="black")
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    st.pyplot(fig)


def plot_books_read_per_month(conn):
    """Plot a bar graph of books read per month."""
    year = datetime.now().year
    query = f"""
        SELECT 
            strftime('%m', datetime(psd.start_time, 'unixepoch', 'localtime')) AS month,
            COUNT(DISTINCT b.title) AS books_read
        FROM page_stat_data psd
        JOIN book b ON psd.id_book = b.id
        WHERE strftime('%Y', datetime(psd.start_time, 'unixepoch', 'localtime')) = '{year}' and
        b.title NOT IN ('KOReader Quickstart Guide', 'Necroscope 003: Blutmesse') and b.id != 10
        GROUP BY month
        ORDER BY month;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()

    df_year = pd.DataFrame(data, columns=["Month", "Books Read"])
    df_year["Month"] = df_year["Month"].astype(int)
    df_year = df_year.set_index("Month").reindex(range(1, 13), fill_value=0)

    st.write("### Year in Review: Books Read Per Month")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df_year.index, df_year["Books Read"], color="lightcoral")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_xlabel("Month")
    ax.set_ylabel("Books Read")
    ax.set_title(f"Books Read in {year}")
    st.pyplot(fig)

def plot_book_completion_over_time(conn):
    """Plot a graph of book completion over time for a selected book."""
    # Query to get the list of books
    book_query = "SELECT id, title FROM book b where b.title NOT IN ('KOReader Quickstart Guide', 'Necroscope 003: Blutmesse') and b.id != 10 ORDER BY title;"
    cursor = conn.cursor()
    cursor.execute(book_query)
    books = cursor.fetchall()

    # Create a dictionary of book IDs and titles for the dropdown
    book_dict = {book[1]: book[0] for book in books}

    # Dropdown for book selection
    selected_book = st.selectbox("Select a book to view its completion over time:", list(book_dict.keys()))

    if selected_book:
        book_id = book_dict[selected_book]

        # Query to fetch reading progress for the selected book
        progress_query = f"""
            SELECT 
                date(datetime(psd.start_time, 'unixepoch', 'localtime')) AS reading_date,
                COUNT(DISTINCT psd.page) AS pages_read
            FROM page_stat_data psd
            WHERE psd.id_book = {book_id}
            GROUP BY reading_date
            ORDER BY reading_date;
        """
        cursor.execute(progress_query)
        progress_data = cursor.fetchall()

        if progress_data:
            # Create a DataFrame to represent the book's progress
            df_progress = pd.DataFrame(progress_data, columns=["Date", "Pages Read"])
            df_progress["Date"] = pd.to_datetime(df_progress["Date"])
            df_progress["Cumulative Pages Read"] = df_progress["Pages Read"].cumsum()

            # Plot the progress
            st.write(f"### Completion Progress for '{selected_book}'")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df_progress["Date"], df_progress["Cumulative Pages Read"], marker="o", linestyle="-", color="blue")
            ax.set_xlabel("Date")
            ax.set_ylabel("Cumulative Pages Read")
            ax.set_title(f"Book Completion Progress: {selected_book}")
            ax.grid(True)

            # Display the plot
            st.pyplot(fig)
        else:
            st.warning(f"No reading progress found for '{selected_book}'.")

def plot_book_completion_over_time(conn):
    """Plot a graph of book completion percentage over time for a selected book."""
    # Query to get the list of books
    book_query = "SELECT id, title FROM book b where b.title NOT IN ('KOReader Quickstart Guide', 'Necroscope 003: Blutmesse') and b.id != 10  ORDER BY title;"
    cursor = conn.cursor()
    cursor.execute(book_query)
    books = cursor.fetchall()

    # Create a dictionary of book IDs and titles for the dropdown
    book_dict = {book[1]: book[0] for book in books}

    # Dropdown for book selection
    selected_book = st.selectbox("Select a book to view its completion progress:", list(book_dict.keys()))

    if selected_book:
        book_id = book_dict[selected_book]

        # Determine the total number of pages for the selected book
        total_pages_query = f"""
            SELECT MAX(page)
            FROM page_stat_data
            WHERE id_book = {book_id};
        """
        cursor.execute(total_pages_query)
        total_pages = cursor.fetchone()[0]

        if not total_pages or total_pages == 0:
            st.warning(f"No pages found for '{selected_book}'. Cannot display progress.")
            return

        # Query to fetch reading progress for the selected book
        progress_query = f"""
            SELECT 
                date(datetime(psd.start_time, 'unixepoch', 'localtime')) AS reading_date,
                COUNT(DISTINCT psd.page) AS pages_read
            FROM page_stat_data psd
            WHERE psd.id_book = {book_id}
            GROUP BY reading_date
            ORDER BY reading_date;
        """
        cursor.execute(progress_query)
        progress_data = cursor.fetchall()

        if progress_data:
            # Create a DataFrame to represent the book's progress
            df_progress = pd.DataFrame(progress_data, columns=["Date", "Pages Read"])
            df_progress["Cumulative Pages Read"] = df_progress["Pages Read"].cumsum()
            df_progress["Completion %"] = (df_progress["Cumulative Pages Read"] / total_pages * 100).clip(upper=100)

            # Assign day indices (Day 1, Day 2, etc.)
            df_progress["Day"] = range(1, len(df_progress) + 1)

            # Stop adding days once the book is 100% complete
            df_incomplete = df_progress[df_progress["Completion %"] < 100]
            df_complete_first = df_progress[df_progress["Completion %"] == 100].head(1)
            df_progress = pd.concat([df_incomplete, df_complete_first], ignore_index=True)

            # Plot the progress
            st.write(f"### Completion Progress for '{selected_book}'")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df_progress["Day"], df_progress["Completion %"], marker="o", linestyle="-", color="blue")
            ax.set_xlabel("Day")
            ax.set_ylabel("Completion %")
            ax.set_title(f"Book Completion Progress: {selected_book}")
            ax.grid(True)
            ax.set_ylim(0, 100)

            # Force X-axis ticks for every day
            days = df_progress["Day"]
            ax.set_xticks(days)  # Set X-axis ticks to every day
            ax.set_xticklabels([f"Day {int(day)}" for day in days], rotation=45, ha="right")

            # Annotate the final completion point
            if df_progress["Completion %"].iloc[-1] == 100:
                ax.text(
                    df_progress["Day"].iloc[-1],
                    100,
                    "Completed",
                    fontsize=10,
                    color="green",
                    va="bottom",
                    ha="center",
                    fontweight="bold"
                )

            # Display the plot
            st.pyplot(fig)
        else:
            st.warning(f"No reading progress found for '{selected_book}'.")



def plot_completion_vs_cumulative_time(conn):
    """Plot a graph of completion percentage vs. cumulative time spent reading in hours."""
    # Query to get the list of books
    book_query = "SELECT id, title FROM book b where b.title NOT IN ('KOReader Quickstart Guide', 'Necroscope 003: Blutmesse') and b.id != 10 ORDER BY title;"
    cursor = conn.cursor()
    cursor.execute(book_query)
    books = cursor.fetchall()

    # Create a dictionary of book IDs and titles for the dropdown
    book_dict = {book[1]: book[0] for book in books}

    # Dropdown for book selection
    selected_book = st.selectbox("Select a book to view completion vs. cumulative time:", list(book_dict.keys()))

    if selected_book:
        book_id = book_dict[selected_book]

        # Determine the total number of pages for the selected book
        total_pages_query = f"""
            SELECT MAX(page)
            FROM page_stat_data
            WHERE id_book = {book_id};
        """
        cursor.execute(total_pages_query)
        total_pages = cursor.fetchone()[0]

        if not total_pages or total_pages == 0:
            st.warning(f"No pages found for '{selected_book}'. Cannot display progress.")
            return

        # Query to fetch reading progress for the selected book
        progress_query = f"""
            SELECT 
                SUM(psd.duration) AS time_spent_seconds,  -- Total time spent in seconds
                COUNT(DISTINCT psd.page) AS pages_read
            FROM page_stat_data psd
            WHERE psd.id_book = {book_id}
            GROUP BY date(datetime(psd.start_time, 'unixepoch', 'localtime'))
            ORDER BY datetime(psd.start_time, 'unixepoch', 'localtime');
        """
        cursor.execute(progress_query)
        progress_data = cursor.fetchall()

        if progress_data:
            # Create a DataFrame to represent the book's progress
            df_progress = pd.DataFrame(progress_data, columns=["Time Spent (seconds)", "Pages Read"])
            df_progress["Cumulative Time (hours)"] = (df_progress["Time Spent (seconds)"].cumsum() / 3600)
            df_progress["Cumulative Pages Read"] = df_progress["Pages Read"].cumsum()
            df_progress["Completion %"] = (df_progress["Cumulative Pages Read"] / total_pages * 100).clip(upper=100)

            # Stop adding data once the book is 100% complete
            df_incomplete = df_progress[df_progress["Completion %"] < 100]
            df_complete_first = df_progress[df_progress["Completion %"] == 100].head(1)
            df_progress = pd.concat([df_incomplete, df_complete_first], ignore_index=True)

            # Plot the progress
            st.write(f"### Completion Progress vs. Cumulative Time (Hours) for '{selected_book}'")
            fig, ax = plt.subplots(figsize=(14, 8))  # Increased figure size
            ax.plot(df_progress["Cumulative Time (hours)"], df_progress["Completion %"], marker="o", linestyle="-", color="purple")
            ax.set_xlabel("Cumulative Time Spent Reading (hours)", fontsize=14)
            ax.set_ylabel("Completion %", fontsize=14)
            ax.set_title(f"Completion Progress vs. Time Spent: {selected_book}", fontsize=16)
            ax.grid(True)
            ax.set_ylim(0, 100)
            ax.set_xlim(0, max(df_progress["Cumulative Time (hours)"]))

            # Force X-axis ticks at 1-hour intervals
            x_ticks = [i for i in range(int(df_progress["Cumulative Time (hours)"].max()) + 2)]
            ax.set_xticks(x_ticks)

            # Force Y-axis ticks at 5% intervals
            y_ticks = [i for i in range(0, 101, 5)]
            ax.set_yticks(y_ticks)

            # Adjust tick label size
            ax.tick_params(axis='both', which='major', labelsize=12)

            # Add padding around the plot
            fig.tight_layout(pad=3.0)

            # Annotate the final completion point
            if df_progress["Completion %"].iloc[-1] == 100:
                ax.text(
                    df_progress["Cumulative Time (hours)"].iloc[-1],
                    100,
                    "Completed",
                    fontsize=12,
                    color="green",
                    va="bottom",
                    ha="center",
                    fontweight="bold"
                )

            # Display the plot
            st.pyplot(fig)
        else:
            st.warning(f"No reading progress found for '{selected_book}'.")


def plot_pages_read_timeline(conn):
    """Plot a timeline of pages read per day in the current year."""
    query = """
        SELECT 
            date(datetime(psd.start_time, 'unixepoch', 'localtime')) AS reading_date,
            COUNT(DISTINCT psd.page) AS pages_read
        FROM page_stat_data psd
        WHERE strftime('%Y', datetime(psd.start_time, 'unixepoch', 'localtime')) = strftime('%Y', 'now')
        GROUP BY reading_date
        ORDER BY reading_date;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()

    # Create DataFrame
    df_timeline = pd.DataFrame(data, columns=["Date", "Pages Read"])
    df_timeline["Date"] = pd.to_datetime(df_timeline["Date"])

    # Plotting
    st.write("### Year Recap Timeline: Pages Read Per Day")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df_timeline["Date"], df_timeline["Pages Read"], marker="o", linestyle="-", color="green")

    # Set x-axis ticks to match unique dates
    ax.set_xticks(df_timeline["Date"])
    ax.set_xticklabels(df_timeline["Date"].dt.strftime("%b %d"), rotation=45, ha="right")  # Format and rotate labels

    ax.set_xlabel("Date")
    ax.set_ylabel("Pages Read")
    ax.set_title("Timeline: Pages Read Per Day (Current Year)")
    ax.grid(True)

    st.pyplot(fig)

def plot_reading_activity_by_day_of_week(conn):
    """Plot reading activity (in minutes) by day of the week for the current year."""
    query = """
        SELECT 
            strftime('%w', datetime(psd.start_time, 'unixepoch', 'localtime')) AS day_of_week,
            SUM(psd.duration) / 60.0 AS total_minutes_read
        FROM page_stat_data psd
        WHERE strftime('%Y', datetime(psd.start_time, 'unixepoch', 'localtime')) = strftime('%Y', 'now')
        GROUP BY day_of_week
        ORDER BY day_of_week;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()

    df_dow = pd.DataFrame(data, columns=["Day of Week", "Minutes Read"])
    df_dow["Day of Week"] = df_dow["Day of Week"].astype(int)
    df_dow["Day Name"] = df_dow["Day of Week"].map({
        0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
        4: "Thursday", 5: "Friday", 6: "Saturday"
    })

    st.write("### Reading Activity by Day of the Week (Current Year)")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df_dow["Day Name"], df_dow["Minutes Read"], color="skyblue")
    ax.set_xlabel("Day of the Week")
    ax.set_ylabel("Minutes Read")
    ax.set_title("Reading Activity by Day of the Week (Current Year)")
    st.pyplot(fig)

def plot_minutes_read_per_month(conn):
    """Plot minutes read per month spanning the current year."""
    query = """
        SELECT 
            strftime('%Y-%m', datetime(psd.start_time, 'unixepoch', 'localtime')) AS reading_month,
            SUM(psd.duration) / 60.0 AS minutes_read
        FROM page_stat_data psd
        WHERE strftime('%Y', datetime(psd.start_time, 'unixepoch', 'localtime')) = strftime('%Y', 'now')
        GROUP BY reading_month
        ORDER BY reading_month;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()

    df_minutes = pd.DataFrame(data, columns=["Month", "Minutes Read"])
    df_minutes["Month"] = pd.to_datetime(df_minutes["Month"])

    current_year = datetime.now().year
    all_months = pd.date_range(start=f"{current_year}-01-01", end=f"{current_year}-12-31", freq="MS")
    df_minutes = df_minutes.set_index("Month").reindex(all_months, fill_value=0).reset_index()

    st.write("### Minutes Read Per Month (Spanning the Year)")
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(df_minutes["index"].dt.strftime('%b'), df_minutes["Minutes Read"], color="blue")
    ax.set_xlabel("Month")
    ax.set_ylabel("Minutes Read")
    ax.set_title("Minutes Read Per Month (Spanning the Year)")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)

def plot_pages_read_per_book(df_books):
    """Plot total pages read per book."""
    st.write("### Pages Read Per Book")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df_books["Book Title"], df_books["Total Pages Read"], color="skyblue")
    ax.set_xlabel("Total Pages Read")
    ax.set_ylabel("Book Title")
    ax.set_title("Pages Read Per Book")
    for bar in bars:
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width())}", va="center", fontsize=10, color="black")
    st.pyplot(fig)

def plot_avg_reading_speed_per_book(df_books):
    """Plot average reading speed per book."""
    st.write("### Average Reading Speed (pages/hour)")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df_books["Book Title"], df_books["Average Reading Speed (pages/hour)"], color="lightgreen")
    ax.set_xticklabels(df_books["Book Title"], rotation=45, ha="right")
    ax.set_xlabel("Book Title")
    ax.set_ylabel("Reading Speed (pages/hour)")
    ax.set_title("Average Reading Speed by Book")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f"{bar.get_height():.2f}", ha="center", fontsize=10, color="black")
    st.pyplot(fig)

def plot_past_30_days_reading(conn):
    """
    Plot time spent reading over the past 30 days based on database data
    and display a summary of total minutes read and average minutes per day.
    """
    try:
        # Get the system's timezone offset
        from datetime import datetime, timezone, timedelta
        import pytz

        local_tz = datetime.now().astimezone().tzinfo
        local_offset_seconds = local_tz.utcoffset(datetime.now()).total_seconds()

        # Query for time spent reading over the past 30 days, adjusted for the system timezone
        past_30_days_query = f"""
            SELECT 
                date(datetime(psd.start_time, 'unixepoch', 0 || ' seconds')) AS reading_date,
                SUM(psd.duration) / 60.0 AS minutes_read
            FROM page_stat_data psd
            WHERE 
                reading_date >= date('now', '-30 days', 0 || ' seconds')
                AND psd.id_book != 10 
        """
        cursor = conn.cursor()
        cursor.execute(past_30_days_query)
        past_30_days_data = cursor.fetchall()

        # Create DataFrame from raw query results
        df_past_30_days = pd.DataFrame(past_30_days_data, columns=["Date", "Minutes Read"])
        df_past_30_days["Date"] = pd.to_datetime(df_past_30_days["Date"])  # Ensure dates are parsed correctly

        # Normalize dates to midnight (strip time component)
        df_past_30_days["Date"] = df_past_30_days["Date"].dt.normalize()

        # Ensure all days in the past 30 days are included
        today = datetime.now()
        date_range = pd.date_range(end=today, periods=30)  # Generate 30 consecutive days up to today
        df_date_range = pd.DataFrame(date_range, columns=["Date"])
        df_date_range["Date"] = df_date_range["Date"].dt.normalize()  # Strip time component

        # Merge query results with the complete date range
        df_past_30_days = pd.merge(df_date_range, df_past_30_days, on="Date", how="left").fillna(0)  # Fill missing days with 0
        df_past_30_days["Minutes Read"] = df_past_30_days["Minutes Read"].astype(float)  # Ensure numeric type for plotting

        # Calculate totals and averages
        total_minutes = df_past_30_days["Minutes Read"].sum()
        avg_minutes_per_day = total_minutes / 30

        # Display summary metrics
        st.write("### Your 30-Day Reading Summary")
        col1, col2 = st.columns(2)
        col1.metric("Total Minutes Read", f"{int(total_minutes)} mins")
        col2.metric("Average Minutes/Day", f"{avg_minutes_per_day:.1f} mins/day")

        # Plot a bar graph for time spent reading over the past 30 days
        st.write("### Time Spent Reading Over the Past 30 Days")
        fig, ax = plt.subplots(figsize=(12, 6))

        # Create a bar chart
        bars = ax.bar(df_past_30_days["Date"].dt.strftime("%b %d"), df_past_30_days["Minutes Read"], color="skyblue")

        # Customize the chart
        ax.set_xlabel("Date")
        ax.set_ylabel("Minutes Read")
        ax.set_title("Reading Activity Over the Past 30 Days")
        plt.xticks(rotation=45, ha="right")  # Rotate X-axis labels for better readability

        # Annotate the bars with exact values
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,  # Center horizontally
                    height + 1,  # Slightly above the bar
                    f"{height:.1f}",  # Display value with one decimal place
                    ha="center",
                    fontsize=8,
                    color="black"
                )

        # Display the chart in Streamlit
        st.pyplot(fig)

    except sqlite3.Error as e:
        st.error(f"An error occurred while querying the database: {e}")



def generate_summary():
    uploaded_file = st.file_uploader("Upload your SQLite3 file", type=["sqlite3", "db"], key="summary_file_uploader")

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_file_path = temp_file.name

        conn = connect_to_database(temp_file_path)

        try:
            # Call modular functions
            df_books = create_books_read_summary(conn)
            create_year_in_review_summary(conn)
            plot_books_read_per_month(conn)
            plot_pages_read_timeline(conn)
            plot_reading_activity_by_day_of_week(conn)
            plot_minutes_read_per_month(conn)
            plot_past_30_days_reading(conn)
            plot_pages_read_per_book(df_books)
            plot_book_completion_over_time(conn)
            plot_completion_vs_cumulative_time(conn)
            plot_avg_reading_speed_per_book(df_books)


        except sqlite3.Error as e:
            st.error(f"An error occurred: {e}")
        finally:
            conn.close()
