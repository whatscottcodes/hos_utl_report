import argparse
import calendar
import pandas as pd
import numpy as np
from paceutils import Participant, Utilization

db_filepath = "V:\\Databases\\PaceDashboard.db"


def long_stays_expense(params):
    utl = Utilization(db_filepath)
    df = utl.los_over_x_df(params, 7, "psych")[
        ["member_id", "admission_date", "discharge_date", "facility", "los"]
    ]
    df["discharge_date"] = pd.to_datetime(df["discharge_date"])
    df["admission_date"] = pd.to_datetime(df["admission_date"])

    fom = pd.to_datetime(params[0])

    df["days_in_prev_month"] = fom - df["admission_date"]
    df["days_in_current_month"] = df["discharge_date"] - fom


def hospital_trend_report(params, month_abr):
    utl = Utilization(db_filepath)
    total_admissions = utl.admissions_count(params, "acute") + utl.admissions_count(
        params, "psych"
    )
    uniques = utl.unique_admissions_count(params, "acute")

    num_days = utl.utilization_days(params, "acute") + utl.utilization_days(
        params, "psych"
    )

    weekend_stays = utl.weekend_admissions_count(
        params, "acute"
    ) + utl.weekend_admissions_count(params, "psych")

    alos = round(num_days / total_admissions, 2)

    long_stays_acute = utl.los_over_x_df(params, 7, "acute")[
        ["member_id", "admission_date", "discharge_date", "facility", "los"]
    ]
    long_stays_psych = utl.los_over_x_df(params, 7, "psych")[
        ["member_id", "admission_date", "discharge_date", "facility", "los"]
    ]

    total_long_stays = long_stays_acute.shape[0] + long_stays_psych.shape[0]

    long_stays_acute["psych_stay"] = "N"
    long_stays_psych["psych_stay"] = "Y"

    long_stays_df = long_stays_acute.append(long_stays_psych, sort=False)
    ppt = Participant(db_filepath)
    long_stays_df["stays_last_6"] = long_stays_acute["member_id"].apply(
        lambda x: (
            ppt.utilization(utl.last_six_months(), "acute", x).shape[0]
            + ppt.utilization(utl.last_six_months(), "psych", x).shape[0]
        )
    )

    stays_string = f"{total_admissions}/{uniques}/{weekend_stays}"
    return (
        pd.DataFrame.from_dict(
            {month_abr: [stays_string, num_days, total_long_stays, alos]}
        ),
        long_stays_df,
    )


def update_trend_spreadsheet(df):
    hosp_trends = pd.read_csv(".\\output\\hospital_trends.csv")
    hosp_trends[df.columns[0]] = df[df.columns[0]]
    hosp_trends.to_csv(".\\output\\hospital_trends.csv", index=False)


def update_long_stays(df, month_name):
    long_stays = pd.read_csv(".\\output\\long_stays.csv")
    ppt = Participant(db_filepath)
    df["Name"] = df["member_id"].apply(lambda x: " ".join(ppt.name(x)[0]))
    df["Dates"] = (
        df["admission_date"].str[5:].str.replace("-", "/")
        + "-"
        + df["discharge_date"].str[5:].str.replace("-", "/")
    )
    df.drop(["member_id", "admission_date", "discharge_date"], inplace=True, axis=1)

    df.rename(
        columns={
            "los": "Days",
            "facility": "Hospital",
            "psych_stay": "Psych. stay Y=Yes",
            "stays_last_6": "Number of hospital stays, including psych. stays, during the 6 months preceding the stay OR since enrollment if enrolled < 6 months when hospitalized",
        },
        inplace=True,
    )
    month_text = month_name.replace("_", " ")

    month_row = {
        "Name": f"In {month_text}",
        "Dates": np.nan,
        "Days": np.nan,
        "Hospital": np.nan,
        "Psych. stay Y=Yes": np.nan,
        "Number of hospital stays, including psych. stays, during the 6 months preceding the stay OR since enrollment if enrolled < 6 months when hospitalized": np.nan,
    }

    df = pd.DataFrame(data=month_row, index=[0]).append(df, sort=False)
    df = df.append(long_stays, sort=False)

    df.to_csv(".\\output\\long_stays.csv", index=False)


def hospital_expense_report(params=None):
    if params is None:
        params = Utilization(db_filepath).last_month()
    else:
        params = params.split(",")
    month_name = (
        calendar.month_abbr[int(params[0].split("-")[1])]
        + "_"
        + params[0].split("-")[0]
    )
    ur, ls = hospital_trend_report(params, month_name)
    update_trend_spreadsheet(ur)
    update_long_stays(ls, month_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--params",
        default=None,
        help="Data range as a tuple, ie ('YYYY-MM-DD', 'YYYY-MM-DD')",
    )

    arguments = parser.parse_args()

    hospital_expense_report(**vars(arguments))

    print("Done")
