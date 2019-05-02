"""Creates two csv files; one for hospital trends and one for long stays.
See report.txt for information on required csv files from Cognify and
naming conventions for script to run correctly.

“Number of hospital stays” is reported as:
total stays / # of ppts / # of weekend admissions.
Example: May had 16 total hospitalizations,
14 different ppts were hospitalized,
and 7 of the admissions were done on a Saturday or Sunday.
"""

import pandas as pd
import numpy as np
import calendar
import sqlite3


def get_month():
    """Gets reporting month from user.
    Args:
        None, input from user; reporting month as an int.

    Returns:
        Reporting month as an int.
    """
    try:
        info = input(
            "Enter the reporting month as a number with year (12/2018): "
        ).split("/")
        return int(info[0]), int(info[1])
    except TypeError:
        print("That is not a number!")
        return get_month()


def load_clean_data():
    """Loads inpatient csv file and filters for acute hospital stays.

    More information about required csv files and naming conventions can be
    found in reports.txt.

    Args:
        None

    Returns:
        inpatient: pandas Dataframes with Training ppts removed and filtered
        for acute hospital stays
    """
    conn = sqlite3.connect("V:\\Databases\\reporting.db")
    inpatient = pd.read_sql(
        """SELECT inpatient.member_id, admission_date, discharge_date, los, facility,
       discharge_reason, admit_reason, admission_type, er,
       observation, days_since_last_admission, days_MD, days_RN,
       time, living_situation, admitted_from, admitting_facility,
       reason, discharge_dx, related, sent_by_oc, aware_ss,
       aware_visit, preventable, w_six_months, dow,
       last, first FROM inpatient JOIN ppts ON inpatient.member_id=ppts.member_id""",
        conn,
        parse_dates=["admission_date", "discharge_date"],
    )

    return inpatient


def month_filter(inpatient, month, year):
    """Create dataframes of stays that count towards the current or
    previous month.

    Args:
        inpatient: pandas Dataframe of actute hosptial stays.
        month: reporting month as int.
        for_long_stays: boolean indicating if this is being called for the
        report of long stays, because we don't care about how many days in the
        month they had inpatient.

    Returns:
        prev_month: pandas dataframe of stays that span the previous and
        current reporting months and need to be attributed to the previous
        month.
        current_month: stays attributed to the current month

    #Note: If a hospital stay spanned 2 months, it was assigned to the month
    that accounted for the most days. If both months accounted for an equal
    number of days, the stay was assigned to the month of discharge. This does
    not matter when calculating the month's stay for the long stays reports.
    """
    last_day = calendar.monthrange(year, month)[1]
    start = pd.to_datetime(str(month) + "/01/" + str(year))
    end = pd.to_datetime(str(month) + "/" + str(last_day) + "/" + str(year))
    print(start, end)
    month_mask = (inpatient.discharge_date >= start) & (inpatient.discharge_date <= end)
    current_month = inpatient[
        (inpatient.admission_type == "Acute Hospital") & month_mask
    ]
    return current_month


def load_current():
    """Loads current csv of hospital trend data for previous months.

    Args:
        None.

    Returns:
        pandas Dataframe of current hospital trend data report
    """
    return pd.read_csv("hospital_trends.csv")


def add_month(hosp_trends, current_month, month):
    """Adds reporting month's data to the hospital_trends dataframe.

    Args:
        hosp_trend: dataframe of current hospital trends.
        current_month: stays found that account to the reporting month.

    Returns:
        hosp_trend: dataframe of current hospital trends with the
        reporting month's data inserted.
    """
    total_stays = current_month.shape[0]
    print(current_month.member_id)
    number_of_ppts = len(current_month.member_id.unique())
    weekend_admissions = sum(
        [date.weekday() > 4 for date in current_month.admission_date]
    )

    hosp_stays = (
        str(total_stays) + "/" + str(number_of_ppts) + "/" + str(weekend_admissions)
    )

    num_of_days = current_month.los.sum()
    num_of_long_stays = current_month[current_month.los >= 7].shape[0]
    avg_LOS = current_month.los.mean()

    abr_month = calendar.month_abbr[month]
    hosp_trends[abr_month] = [
        hosp_stays,
        num_of_days,
        num_of_long_stays,
        avg_LOS,
        np.nan,
    ]

    return hosp_trends


def update_long_stays(curr_long_stays, current_month, month):
    """Takes the current long stay dataframe and adds reporting month's data.

    Args:
        curr_long_stays: dataframe of current long stay data.
        current_month: stays found that account to the reporting month.
        month: reporting month as int.

    Returns:
        None: saves updated copy of long_stays.csv
    """
    long_stays = current_month[current_month.los >= 7].copy()
    print(long_stays)
    long_stays["Psych. stay Y=Yes"] = np.where(
        long_stays.facility == "Butler Hospital", "Y", ""
    )

    long_stays["Dates"] = (
        long_stays.admission_date.dt.strftime("%m-%d").str.replace("-", "/")
        + "-"
        + long_stays.discharge_date.dt.strftime("%m-%d").str.replace("-", "/")
    )
    long_stay_IDs = long_stays.member_id.tolist()

    # finds any stays in the last 6 months
    six_month_mask = (
        (inpatient.admission_type == "Acute Hospital")
        & (inpatient.discharge_date < "02/28/2019")
        & (inpatient.discharge_date > "9/01/2018")
    )

    prior_hosp = (
        inpatient[inpatient.member_id.isin(long_stay_IDs) & six_month_mask]
        .groupby("member_id")
        .count()["admission_date"]
    )

    long_stays["stays"] = ""

    for member in prior_hosp.index.tolist():
        i = long_stays[long_stays.member_id == member].index.tolist()
        long_stays.at[i, "stays"] = prior_hosp[member]

    final_long_stays = long_stays.copy()
    final_long_stays["name"] = (
        final_long_stays["first"] + " " + final_long_stays["last"]
    )
    col_order = ["name", "Dates", "Psych. stay Y=Yes", "los", "stays", "facility"]

    final_long_stays = final_long_stays[col_order]

    abr_month = calendar.month_abbr[month]
    year = pd.datetime.today().year

    month_line = pd.DataFrame(
        {
            "name": "In " + str(abr_month) + " " + str(year),
            "los": np.nan,
            "stays": np.nan,
            "facility": np.nan,
        },
        index=[0],
    )
    final_long_stays = final_long_stays.append(
        month_line, ignore_index=False, sort=False
    )
    final_long_stays = final_long_stays.sort_index().reset_index(drop=True)

    final_rename_dict = {
        "name": "Name",
        "los": "Days",
        "stays": (
            "Number of hospital stays, including"
            "psych. stays, during the 6 months "
            "preceding the stay OR since enrollment "
            "if enrolled < 6 months when "
            "hospitalized"
        ),
        "facility": "Hospital",
    }

    final_long_stays.rename(columns=final_rename_dict, inplace=True)
    long_stays_updated = pd.concat(
        [final_long_stays, curr_long_stays], ignore_index=True, sort=False
    )
    long_stays_updated.to_csv("long_stays_updated.csv", index=False)


if __name__ == "__main__":
    print("Ensure all files are in the folder, saved as CSV and" "named as follows;")
    print("inpatient")
    print("hospital_trends")
    print("long_stays")
    month, year = get_month()
    inpatient = load_clean_data()
    current_month = month_filter(inpatient, month, year)
    current_hosp_trends = load_current()
    current_updated = add_month(current_hosp_trends, current_month, month)

    current_updated.to_csv("hospital_trends.csv", index=False)
    curr_long_stays = pd.read_csv("long_stays.csv")
    update_long_stays(curr_long_stays, current_month, month)
    print("Done")
