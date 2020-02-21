# Hospital Report
Script for creating two csv files that can be used to update information in a risk-management related hospital expense report. These files contain admission summary information and a list of long (7+) stays.

## Requirements

All required packages are in the requirements.txt file. There is also an included environment.yml file for setting up a conda environment. Requires paceutils package to be installed in environment - use pip install e <local_path/to/pace_utils>.

### PaceUtils

Requires that the paceutils package to be installed. Can be found at http://github.com/whatscottcodes/paceutils.

Requires a SQLite database set up to the specifications in https://github.com/whatscottcodes/database_mgmt

## Use

Script can be run with no parameters to update files for the previous month. To run for other months pass YYYY-MM-DD, YYYY-MM-DD to the params argument.


