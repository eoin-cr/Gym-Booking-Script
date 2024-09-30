# script.py
import requests
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
num = os.getenv("STUDENT_NUMBER")
timeout_after_x_hrs = True
time_to_timeout = 3

hours_before_slot_booking_opens = 2
seconds_before_to_start_looking = 60 * 60 * hours_before_slot_booking_opens

selected_time = input(
    "Please enter the session starting time in the format HHMM, e.g. 2030.  Otherwise write now to start searching immediately: "
)


def current_time_in_seconds_func():
    now = datetime.now()
    current_time_secs = int(now.strftime("%S"))
    current_time_mins = int(now.strftime("%M"))
    current_time_hrs = int(now.strftime("%H"))
    return current_time_hrs * 3600 + current_time_mins * 60 + current_time_secs


if selected_time != "now":
    # The gym selection only activates if you don't select now because I assume
    # if you're just looking for a gym slot immediately you don't really mind
    # which gym you get
    # gym = input(
    #     "Please enter whether you want the Poolside or Performance gym.  If you don't mind simply hit enter: "
    # )
    # Turning time into seconds after 0000 to simplify things
    selected_time_in_seconds = (
        int(selected_time[:-2]) * 3600 + int(selected_time[2:]) * 60
    )
    print(f"Selected time in seconds: {selected_time_in_seconds}")

    # Get the current time and convert to seconds
    current_time_in_seconds = current_time_in_seconds_func()
    now = datetime.now()
    print(f'Time: {now.strftime("%H:%M:%S")}')
    print(f"Current time in seconds: {current_time_in_seconds}")

    # Checks if the selected time is before the current time - i.e. tomorrow
    if current_time_in_seconds < selected_time_in_seconds:
        # Bookings open 3 hrs before the gym time, so if it's less than 3 hrs
        # before the gym time, start searching immediately
        if (
            current_time_in_seconds + seconds_before_to_start_looking
            > selected_time_in_seconds
        ):
            time_to_sleep = 0
        else:
            # If it's for the same day, simply wait however many seconds it is
            # until a minute before the selected time
            time_to_sleep = (
                selected_time_in_seconds
                - current_time_in_seconds
                - (seconds_before_to_start_looking + 1)
            )
    else:
        if (
            86399 - current_time_in_seconds + selected_time_in_seconds
            < seconds_before_to_start_looking
        ):
            time_to_sleep = 0
        else:
            # If it is tomorrow, get the seconds left in the day, and add that to
            # the selected time and minus a minute to get the time it needs
            # to wait
            time_to_sleep = (
                86399
                - current_time_in_seconds
                + selected_time_in_seconds
                - (seconds_before_to_start_looking + 1)
            )

    print("Going to sleep!")

    # Sleep until a minute before the booking opens
    time.sleep(time_to_sleep)

    print("Wakey wakey!")
else:
    print("Searching!")

login_sql = ""

start_time_in_seconds = int(current_time_in_seconds_func())

# Will keep searching until an opening is found
while login_sql == "":
    # The way the UCD gym booking system works is that there is a main page
    # that lists all the gym opening times (base_url). If there is an opening
    # and you can book you will be able to go to the next page (login_url)
    # and enter your student number.  Often you would have to include the
    # sql in the post, but with the way the gym servers are set up, you
    # can simply put it in the url.  Once you are at the login_url page
    # in theory you should be able to make a post with your student number
    # and it will book you in
    base_url = "https://hub.ucd.ie/usis/W_HU_MENU.P_PUBLISH?p_tag=GYMBOOK"
    base_response = requests.get(base_url).text
    base_response = base_response.split("\n")
    base_sql = ""
    counter = 0
    for line in base_response:
        counter += 1

    for i in range(counter):
        # If there is an opening at the time we want, the base_url page will
        # contain a HTML line which says something like
        # <TD><a_href=[SQL url]>Book</TD>.  5 lines above will contain the
        # time.  So if a line like this is found with the time slot we want
        # 5 lines above, we know that's the one we want so we ignore the
        # rest of the lines and remove the HTML stuff to just get
        # left with the SQL url
        #         if 'Book' in line and 'TD' in line:
        if selected_time != "now":
            formatted_time = selected_time[:-2] + ":" + selected_time[2:]
            # if gym is not None:
            # Checks for the section containing your time, gym choice, and
            # whether there's a booking
            if (
                formatted_time in base_response[i]
                and "Poolside" in base_response[i + 1]
                and "Book" in base_response[i + 5]
                and "TD" in base_response[i + 5]
            ):
                line = base_response[i + 5]
                base_sql = line[13:-16]
            # else:
            #     # Checks for the section containing your time and whether
            #     # there's a booking
            #     if (
            #         formatted_time in base_response[i]
            #         and "Book" in base_response[i + 5]
            #         and "TD" in base_response[i + 5]
            #     ):
            #         line = base_response[i + 5]
            #         base_sql = line[13:-16]

        # Just looks for any like where there's the option to book
        elif "Book" in base_response[i] and "TD" in base_response[i]:
            line = base_response[i]
            base_sql = line[13:-16]

    if base_sql != "":
        print(f"---\n{base_sql}")

        # We now get the HTML from the login_url site
        login_url = "https://hub.ucd.ie/usis/" + base_sql
        login_response = requests.get(login_url).text
        login_response = login_response.split("\n")

        # Once again we look for a specific line which contains the sql url we
        # want, except this time it's found by looking for a line which
        # contains `name="p_parameters"`
        for line in login_response:
            if 'name="p_parameters"' in line:
                login_sql = line[48:-4]

        if login_sql != "":
            print(f"---\n{login_sql}\n---")
            # We now have the sql url which we will post with our student number
            book_url = "https://hub.ucd.ie/usis/!W_HU_REPORTING.P_RUN_SQL"
            data = {
                "p_query": "SW-GYMANON",
                "p_confirmed": "Y",
                "p_parameters": login_sql,
                "MEMBER_NO": num,
            }
            booking = requests.post(book_url, data=data, allow_redirects=True)

            # Trying this to see what happens
            diff_url = "https://hub.ucd.ie/usis/W_HU_REPORTING.P_RUN_SQL"
            diff_booking = requests.post(diff_url, data=data, allow_redirects=True)
            print(f"---\nDifferent Response\n{diff_booking.text}\n---")

            # This post will bring us to another page which would automatically
            # redirect a browser, however, we have to find the url to make the
            # next request with.  This intermediary page was especially
            # annoying to work with as I wasn't certain why I was getting sent
            # to this page or how to get the url to get to the final page :)

            # Seems like this intermediary page no longer exists.
            # booking = booking.text.split('\n')
            # for line in booking:
            #     if 'refresh' in line:
            #         booking_conf = line[42:-2]
            #         break
            #
            # book_conf_url = "https://hub.ucd.ie/usis/" + booking_conf
            # book_conf_req = requests.get(book_conf_url).text

            book_conf_req = booking.text

            # We're now on the final page!  All we have to do now is emulate
            # pressing the confirm booking button with another post request
            # and we'll have a slot
            booking = book_conf_req.split("\n")
            for line in booking:
                if "Confirm Booking" in line:
                    booking_conf = line[121:-21]
                    break

            print(f"---\n{booking_conf}\n---")
            booked_url = "https://hub.ucd.ie/usis/" + booking_conf
            data = {
                "p_query": "SW-GYMBOOK",
                "p_confirmed": "Y",
                "p_parameters": booking_conf,
            }
            booked_request = requests.post(booked_url, data=data)

            # We should now have a booking in the gym!
            print("Booked!")

            # Displays current time
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print(f"Current Time = {current_time}")

    # Check whether the stated timeout limit has been reached
    elif (
        timeout_after_x_hrs
        and current_time_in_seconds_func() - start_time_in_seconds
        > time_to_timeout * 3600
    ):
        print("Run time exceeded timeout limit, program stopped.")
        login_sql = "stopped"

    # Check whether it's after 20:46 as the last gym slot seems to be at 20:45
    #     elif current_time_in_seconds_func() > 10:
    elif current_time_in_seconds_func() > 163260:
        print("Exceeded closing time of last gym slot, program stopped")
        login_sql = "stopped"

    # Wait a second so we aren't throwing too many requests at the server
    else:
        time.sleep(1)
