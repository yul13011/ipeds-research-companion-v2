# The local database: inventory

Written by `scripts/database_inventory.py` after each full rebuild. Do not edit by hand; run the script again.

`data/ipeds_v2.sqlite`, generated 2026-11-25.

| | |
| --- | ---: |
| Tables | 106 |
| Rows | 40,380,293 |
| File size | 3.27 GB (3,268,206,592 bytes) |
| Releases | 10 (2015-16 to 2024-25) |

Tables and rows by layer:

| Layer | Tables | Rows |
| --- | ---: | ---: |
| survey data | 59 | 33,333,458 |
| IPEDS codebook | 7 | 150,853 |
| dictionary | 16 | 6,873 |
| build result | 17 | 6,858,764 |
| housekeeping | 7 | 30,345 |

Releases loaded:

| Release year | Release | Status |
| --- | --- | --- |
| 2015-16 | IPEDS_2015-16_Final | final |
| 2016-17 | IPEDS_2016-17_Final | final |
| 2017-18 | IPEDS_2017-18_Final | final |
| 2018-19 | IPEDS_2018-19_Final | final |
| 2019-20 | IPEDS_2019-20_Final | final |
| 2020-21 | IPEDS_2020-21_Final | final |
| 2021-22 | IPEDS_2021-22_Final | final |
| 2022-23 | IPEDS_2022-23_Final | final |
| 2023-24 | IPEDS_2023-24_Final | final |
| 2024-25 | IPEDS_2024-25_Provisional | provisional |

The layers:
- **survey data:** the IPEDS survey tables, one per survey file, stacked across releases (a `year` column holds the release year: 2024 for 2024-25). Each is described by its subject and IPEDS's title in the latest release that has it;
- **IPEDS codebook:** the codebook tables that come with each release (tables, variables, code labels);
- **dictionary:** the CSV tables of the `dictionary` folder, loaded as they are (`dict_` + the file name);
- **build result:** tables the build works out from the data and the dictionary (directory, groups, tests in every year, the years of each measure);
- **housekeeping:** the build's own records (what was loaded and cleaned, fingerprints for the fast build) and SQLite's statistics.

## Survey data (59 tables, 33,333,458 rows)

| Table | What it holds | Key columns | Columns | Rows | Releases | 2015-16 | 2016-17 | 2017-18 | 2018-19 | 2019-20 | 2020-21 | 2021-22 | 2022-23 | 2023-24 | 2024-25 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ADM` | Admissions: Admission considerations, applicants, admissions, and test scores | UNITID, year | 62 | 20,296 | 10 (2015-16 to 2024-25) | 2,212 | 2,069 | 2,075 | 2,039 | 2,011 | 1,989 | 1,981 | 1,991 | 1,973 | 1,956 |
| `AL` | Academic libraries: Academic Libraries, Fiscal year 2024 | UNITID, year | 40 | 38,807 | 10 (2015-16 to 2024-25) | 4,266 | 4,142 | 4,074 | 3,849 | 3,834 | 3,788 | 3,765 | 3,741 | 3,696 | 3,652 |
| `CDEP` | Programs offered: Number of programs offered and number of programs offered via distance education, by award level: July 1, 2023 to June 30, 2024 | UNITID, year, CIPCODE | 44 | 2,413,960 | 10 (2015-16 to 2024-25) | 238,922 | 237,468 | 239,696 | 240,794 | 240,412 | 238,689 | 241,826 | 244,056 | 244,950 | 247,147 |
| `COST1` | Published charges: Application fees, tuition and required fees, food and housing for undergraduate and graduate students | UNITID, year | 228 | 5,867 | 1 (2024-25 to 2024-25) |  |  |  |  |  |  |  |  |  | 5,867 |
| `COST2_FINANCIALAID` | Financial aid, full-time first-time students: Financial aid for full-time, first-time degree/certificate-seeking undergraduate students, 2021-22 to 2024-25 | UNITID, year | 223 | 5,406 | 1 (2024-25 to 2024-25) |  |  |  |  |  |  |  |  |  | 5,406 |
| `COST2_NETPRICE` | Net price: Average net price for full-time, first-time degree/certificate-seeking undergraduate students, 2021-22 to 2024-25 | UNITID, year | 56 | 5,406 | 1 (2024-25 to 2024-25) |  |  |  |  |  |  |  |  |  | 5,406 |
| `CUSTOMCGIDS` | Custom comparison groups | UNITID, year | 9 | 436,168 | 10 (2015-16 to 2024-25) | 49,864 | 43,599 | 43,449 | 42,311 | 41,750 | 41,176 | 40,907 | 40,737 | 40,611 | 51,764 |
| `C_A` | Awards by program: Awards/degrees conferred by program (6-digit CIP code), award level, race/ethnicity, and gender: July 1, 2023 to June 30, 2024 | UNITID, year, AWLEVEL, MAJORNUM, CIPCODE | 35 | 16,227,735 | 10 (2015-16 to 2024-25) | 1,622,535 | 1,626,744 | 1,655,049 | 1,541,626 | 1,540,765 | 1,596,906 | 1,631,062 | 1,656,179 | 1,668,398 | 1,688,471 |
| `C_B` | Award recipients: Number of students receiving awards/degrees, by race/ethnicity and gender: July 1, 2023 to June 30, 2024 | UNITID, year | 42 | 63,640 | 10 (2015-16 to 2024-25) | 7,291 | 6,903 | 6,754 | 6,534 | 6,234 | 6,124 | 6,054 | 6,005 | 5,914 | 5,827 |
| `C_C` | Award recipients by level: Number of students receiving awards/degrees, by award level and by gender, race/ethnicity and age categories: July 1, 2023 to June 30, 2024 | UNITID, year, AWLEVELC | 20 | 162,225 | 10 (2015-16 to 2024-25) | 17,155 | 16,674 | 16,464 | 16,141 | 15,550 | 15,942 | 15,984 | 16,146 | 16,065 | 16,104 |
| `DRVADM` | Admissions (derived): Frequently used derived variables for admissions. Selectivity and admissions yield | UNITID, year | 14 | 20,111 | 10 (2015-16 to 2024-25) | 2,212 | 2,052 | 2,047 | 2,013 | 2,013 | 1,966 | 1,963 | 1,964 | 1,950 | 1,931 |
| `DRVAL` | Library indicators: Frequently used/derived variables Academic library indicators: Fiscal year 2024 | UNITID, year | 21 | 41,552 | 10 (2015-16 to 2024-25) | 4,564 | 4,445 | 4,384 | 4,140 | 4,087 | 4,027 | 4,009 | 4,008 | 3,968 | 3,920 |
| `DRVC` | Completions (derived): Frequently used derived variables (C): Completions, July 1, 2023 to June 30, 2024 | UNITID, year | 24 | 64,102 | 10 (2015-16 to 2024-25) | 7,330 | 6,956 | 6,795 | 6,578 | 6,276 | 6,179 | 6,096 | 6,049 | 5,967 | 5,876 |
| `DRVCOST` | Cost of attendance (derived): Frequently used derived variables (Cost): Total cost of attendance | UNITID, year | 15 | 3,388 | 1 (2024-25 to 2024-25) |  |  |  |  |  |  |  |  |  | 3,388 |
| `DRVEF` | Fall enrollment (derived): Frequently used derived variables (EF): Fall enrollment 2024 | UNITID, year | 88 | 63,203 | 10 (2015-16 to 2024-25) | 7,230 | 6,820 | 6,677 | 6,355 | 6,204 | 6,129 | 6,051 | 5,979 | 5,915 | 5,843 |
| `DRVEF12` | 12-month enrollment (derived): Frequently used derived variables (E12): 12-month enrollment, 2023-24 | UNITID, year | 63 | 64,007 | 10 (2015-16 to 2024-25) | 7,322 | 6,951 | 6,785 | 6,562 | 6,272 | 6,169 | 6,087 | 6,037 | 5,960 | 5,862 |
| `DRVF` | Finance (derived): Frequently used/derived variables Finance (F): Fiscal year 2024 | UNITID, year | 145 | 63,967 | 10 (2015-16 to 2024-25) | 7,304 | 6,917 | 6,772 | 6,420 | 6,282 | 6,204 | 6,118 | 6,053 | 5,982 | 5,915 |
| `DRVGR` | Graduation rates (derived): Frequently used derived variables (GR) 150% of normal time to complete - cohort year 2017 (4-year) and cohort year 2020 (2-year) institutions | UNITID, year | 38 | 56,494 | 10 (2015-16 to 2024-25) | 6,425 | 6,085 | 5,956 | 5,700 | 5,555 | 5,488 | 5,415 | 5,376 | 5,275 | 5,219 |
| `DRVHR` | Human resources (derived): Frequently used/derived variables Human resources (HR): Fall 2024 | UNITID, year | 28 | 63,930 | 10 (2015-16 to 2024-25) | 7,307 | 6,897 | 6,752 | 6,430 | 6,276 | 6,201 | 6,117 | 6,049 | 5,989 | 5,912 |
| `DRVIC` | Cost of attendance (earlier releases): Frequently used derived variables (IC): Total cost of attendance | UNITID, year | 15 | 32,676 | 9 (2015-16 to 2023-24) | 4,093 | 3,852 | 3,753 | 3,624 | 3,535 | 3,479 | 3,456 | 3,465 | 3,419 |  |
| `DRVOM` | Outcome Measures (derived): Frequently used derived variables (OM) Award and enrollment rates of degree/certificate-seeking undergraduates, 2015-16 cohort | UNITID, year | 130 | 33,781 | 9 (2016-17 to 2024-25) |  | 4,001 | 3,987 | 3,821 | 3,740 | 3,695 | 3,660 | 3,661 | 3,626 | 3,590 |
| `EAP` | Staff by occupation and tenure: Number of staff by occupational category, faculty and tenure status:  Fall 2024 | UNITID, year, EAPCAT | 14 | 3,009,834 | 10 (2015-16 to 2024-25) | 317,177 | 320,068 | 316,295 | 306,261 | 299,568 | 293,462 | 291,357 | 291,882 | 288,505 | 285,259 |
| `EF` | Fall enrollment by gender and level: Gender, attendance status, and level of student: Fall 2024 | UNITID, year, EFLEVEL | 12 | 447,552 | 10 (2015-16 to 2024-25) | 50,624 | 47,938 | 47,101 | 44,877 | 43,777 | 43,458 | 43,074 | 42,660 | 42,268 | 41,775 |
| `EFA` | Fall enrollment: Race/ethnicity, gender, attendance status, and level of student: Fall 2024 | UNITID, year, EFALEVEL | 40 | 1,215,489 | 10 (2015-16 to 2024-25) | 137,017 | 129,919 | 127,770 | 121,842 | 118,917 | 117,881 | 116,965 | 116,155 | 115,190 | 113,833 |
| `EFA_DIST` | Fall enrollment by distance education: Distance education status and level of student: Fall 2024 | UNITID, year, EFDELEV | 12 | 225,309 | 10 (2015-16 to 2024-25) | 24,037 | 22,996 | 22,594 | 21,567 | 22,862 | 22,663 | 22,469 | 22,247 | 22,055 | 21,819 |
| `EFB` | Fall enrollment by age: Age category, gender, attendance status, and level of student: Fall 2024 | UNITID, year, EFBAGE, LSTUDY | 14 | 1,250,726 | 10 (2015-16 to 2024-25) | 190,216 | 84,984 | 176,740 | 81,449 | 164,753 | 78,024 | 161,174 | 78,105 | 158,922 | 76,359 |
| `EFC` | Residence of first-time students: Residence and migration of first-time freshman: Fall 2024 (optional) | UNITID, year, EFCSTATE | 6 | 551,514 | 10 (2015-16 to 2024-25) | 39,592 | 71,934 | 39,525 | 70,448 | 39,209 | 68,859 | 40,124 | 71,359 | 40,345 | 70,119 |
| `EFCP` | Fall enrollment by major: Major field of study, race/ethnicity, gender, attendance status, and level of student: Fall 2024 | UNITID, year, EFCIPLEV | 37 | 828,262 | 5 (2016-17 to 2024-25) |  | 165,124 |  | 164,541 |  | 164,094 |  | 165,864 |  | 168,639 |
| `EFD` | Entering class and retention: Total entering class, retention rates, and student-to-faculty ratio: Fall 2024 | UNITID, year | 18 | 60,279 | 10 (2015-16 to 2024-25) | 6,916 | 6,507 | 6,371 | 6,054 | 5,885 | 5,845 | 5,771 | 5,706 | 5,646 | 5,578 |
| `EFFY` | 12-month headcount: 12-month unduplicated headcount: 2023-24 | UNITID, year, EFFYALEV | 39 | 633,211 | 10 (2015-16 to 2024-25) | 16,475 | 15,727 | 15,395 | 14,944 | 14,326 | 103,723 | 103,615 | 117,543 | 116,437 | 115,026 |
| `EFFY_DIST` | 12-month headcount by distance education: 12-month unduplicated headcount by distance education status and level of student: 2023-24 | UNITID, year, EFFYDLEV | 7 | 112,306 | 5 (2020-21 to 2024-25) |  |  |  |  |  | 22,870 | 22,627 | 22,493 | 22,319 | 21,997 |
| `EFFY_HS` | 12-month headcount, dual enrollment: 12-month unduplicated headcount of dual enrolled students by race/ethnicity and gender: 2023-24 | UNITID, year | 32 | 4,972 | 2 (2023-24 to 2024-25) |  |  |  |  |  |  |  |  | 2,591 | 2,381 |
| `EFIA` | Instructional activity: 12-month instructional activity: 2023-24 | UNITID, year | 11 | 64,003 | 10 (2015-16 to 2024-25) | 7,322 | 6,951 | 6,785 | 6,562 | 6,272 | 6,169 | 6,086 | 6,036 | 5,959 | 5,861 |
| `FLAGS` | Response status: Response status for all survey components | UNITID, year | 136 | 66,957 | 10 (2015-16 to 2024-25) | 7,647 | 7,521 | 7,153 | 6,857 | 6,559 | 6,440 | 6,289 | 6,256 | 6,163 | 6,072 |
| `F_F1A` | Finance, public (GASB): Public institutions - GASB 34/35: Fiscal year 2024 | UNITID, year | 209 | 19,533 | 10 (2015-16 to 2024-25) | 1,986 | 1,986 | 1,978 | 1,964 | 1,961 | 1,949 | 1,946 | 1,936 | 1,916 | 1,911 |
| `F_F2` | Finance, private nonprofit (FASB): Private not-for-profit institutions or Public institutions using FASB: Fiscal year 2024 | UNITID, year | 230 | 18,301 | 10 (2015-16 to 2024-25) | 1,922 | 1,888 | 1,884 | 1,849 | 1,836 | 1,819 | 1,805 | 1,782 | 1,766 | 1,750 |
| `F_F3` | Finance, for-profit: Private for-profit institutions: Fiscal year 2024 | UNITID, year | 159 | 23,783 | 10 (2015-16 to 2024-25) | 3,020 | 2,782 | 2,657 | 2,379 | 2,272 | 2,244 | 2,173 | 2,120 | 2,090 | 2,046 |
| `GR` | Graduation rates (150%): Graduation rate data, 150% of normal time to complete - cohort year 2017 (4-year) and cohort year 2020 (2-year) institutions | UNITID, year, GRTYPE | 37 | 520,501 | 10 (2015-16 to 2024-25) | 57,349 | 55,737 | 54,747 | 51,906 | 50,493 | 50,103 | 49,547 | 48,217 | 51,391 | 51,011 |
| `GR200` | Graduation rates (200%): Graduation rate data, 200% of normal time to complete - cohort year 2015  (4-year) and cohort year 2019 (less-than-4-year)  institutions | UNITID, year | 28 | 52,503 | 10 (2015-16 to 2024-25) | 5,922 | 5,652 | 5,534 | 5,301 | 5,130 | 5,094 | 5,068 | 5,010 | 4,954 | 4,838 |
| `GR_GENDER` | Graduation cohorts, gender unknown: Gender unknown reported in revised cohorts | UNITID, year | 8 | 10,651 | 2 (2022-23 to 2023-24) |  |  |  |  |  |  |  | 5,376 | 5,275 |  |
| `GR_L2` | Graduation rates, less-than-2-year schools: Graduation rate data, 150% of normal time to complete - cohort year 2020 (less-than-2-year institutions) | UNITID, year | 22 | 16,553 | 10 (2015-16 to 2024-25) | 1,887 | 1,722 | 1,691 | 1,678 | 1,651 | 1,635 | 1,615 | 1,591 | 1,548 | 1,535 |
| `GR_PELL_SSL` | Graduation rates, Pell and Subsidized Stafford loan recipients: Graduation rate data for Pell Grant and Subsidized Stafford loan recipients, 150% of normal time to complete - cohort year 2017 (4-year) and cohort year 2020 (2-year) institutions | UNITID, year, PSGRTYPE | 27 | 77,248 | 9 (2016-17 to 2024-25) |  | 9,325 | 9,118 | 8,765 | 8,505 | 8,440 | 8,357 | 8,345 | 8,220 | 8,173 |
| `HD` | Directory: Directory information | UNITID, year | 94 | 66,957 | 10 (2015-16 to 2024-25) | 7,647 | 7,521 | 7,153 | 6,857 | 6,559 | 6,440 | 6,289 | 6,256 | 6,163 | 6,072 |
| `IC` | Institutional characteristics: Educational offerings, organization, admissions, services and athletic associations | UNITID, year | 137 | 64,970 | 10 (2015-16 to 2024-25) | 7,418 | 7,047 | 6,882 | 6,668 | 6,362 | 6,264 | 6,179 | 6,138 | 6,049 | 5,963 |
| `ICMISSION` | Mission statement | UNITID, year | 4 | 64,302 | 10 (2015-16 to 2024-25) | 7,333 | 6,953 | 6,793 | 6,583 | 6,281 | 6,178 | 6,095 | 6,147 | 6,049 | 5,890 |
| `IC_AY` | Charges, academic year (earlier releases): Student charges for academic year programs | UNITID, year | 122 | 36,886 | 9 (2015-16 to 2023-24) | 4,607 | 4,397 | 4,281 | 4,125 | 3,993 | 3,911 | 3,871 | 3,876 | 3,825 |  |
| `IC_PCCAMPUSES` | Branch campuses: Branch campus locations listed on College Navigator | UNITID, year | 171 | 1,551 | 3 (2021-22 to 2023-24) |  |  |  |  |  |  | 533 | 504 | 514 |  |
| `IC_PY` | Charges by program (earlier releases): Student charges by program (vocational programs) | UNITID, year | 70 | 21,329 | 9 (2015-16 to 2023-24) | 2,723 | 2,556 | 2,511 | 2,453 | 2,285 | 2,266 | 2,222 | 2,172 | 2,141 |  |
| `OM` | Outcome Measures: Award and enrollment data at four, six and eight years for  entering undergraduate cohorts from 2015-16 degree granting institutions | UNITID, year, OMCHRT | 36 | 415,183 | 10 (2015-16 to 2024-25) | 13,577 | 13,202 | 51,601 | 50,006 | 48,535 | 48,200 | 47,779 | 47,892 | 47,362 | 47,029 |
| `SAL_IS` | Salaries, instructional staff: Number and salary outlays for full-time nonmedical instructional staff, by  gender, and academic rank:  Academic year 2024-25 | UNITID, year, ARANK | 63 | 158,406 | 10 (2015-16 to 2024-25) | 16,943 | 16,558 | 16,459 | 15,939 | 15,683 | 15,464 | 15,381 | 15,455 | 15,308 | 15,216 |
| `SAL_NIS` | Salaries, non-instructional staff: Number and salary outlays for full-time nonmedical  noninstructional staff by occupation: Academic year 2024-25 | UNITID, year | 30 | 41,908 | 10 (2015-16 to 2024-25) | 4,726 | 4,521 | 4,449 | 4,192 | 4,089 | 4,035 | 4,013 | 4,008 | 3,961 | 3,914 |
| `SFA` | Student financial aid: Student financial aid: 2023-24 | UNITID, year | 93 | 5,575 | 1 (2024-25 to 2024-25) |  |  |  |  |  |  |  |  |  | 5,575 |
| `SFAV` | Veterans' benefits: Military Servicemembers and Veteran's Benefits, 2023-24 | UNITID, year | 23 | 62,607 | 10 (2015-16 to 2024-25) | 7,185 | 6,774 | 6,605 | 6,329 | 6,117 | 6,064 | 5,974 | 5,898 | 5,838 | 5,823 |
| `SFA_P1` | Student financial aid (earlier releases): Student financial aid: {Y-1}-{Y:yy} | UNITID, year | 107 | 54,920 | 9 (2015-16 to 2023-24) | 6,959 | 6,544 | 6,394 | 6,114 | 5,909 | 5,859 | 5,779 | 5,709 | 5,653 |  |
| `SFA_P2` | Net price (earlier releases): Student financial aid and net price: {Y-1}-{Y:yy} | UNITID, year | 249 | 54,920 | 9 (2015-16 to 2023-24) | 6,959 | 6,544 | 6,394 | 6,114 | 5,909 | 5,859 | 5,779 | 5,709 | 5,653 |  |
| `S_IS` | Full-time instructional staff: Full-time instructional staff, by faculty and tenure status, academic rank, race/ethnicity, and gender (Degree-granting institutions): Fall 2024 | UNITID, year, SISCAT | 35 | 648,786 | 10 (2015-16 to 2024-25) | 63,410 | 67,870 | 67,534 | 66,184 | 65,135 | 63,844 | 63,586 | 64,075 | 63,759 | 63,389 |
| `S_NH` | New hires: New hires by occupational category, race/ethnicity, and gender (Degree-granting institutions):  Fall 2024 | UNITID, year, SNHCAT | 36 | 406,944 | 10 (2015-16 to 2024-25) | 36,082 | 41,596 | 42,262 | 41,963 | 41,633 | 38,950 | 40,720 | 41,926 | 41,134 | 40,678 |
| `S_OC` | Staff by occupation: Full- and part-time staff by occupational category, race/ethnicity, and gender:  Fall 2024 | UNITID, year, STAFFCAT | 36 | 1,917,162 | 10 (2015-16 to 2024-25) | 211,925 | 204,970 | 202,049 | 194,843 | 190,684 | 186,176 | 184,654 | 183,548 | 180,289 | 178,024 |
| `S_SIS` | Instructional staff by rank: Full-time instructional staff, by academic rank, faculty and tenure status  (Degree-granting institutions): Fall 2024 | UNITID, year, FACSTAT | 10 | 214,844 | 10 (2015-16 to 2024-25) | 21,600 | 22,699 | 22,505 | 21,784 | 21,418 | 21,049 | 20,980 | 21,088 | 20,937 | 20,784 |

## IPEDS codebook (7 tables, 150,853 rows)

| Table | What it holds | Key columns | Columns | Rows | Releases | 2015-16 | 2016-17 | 2017-18 | 2018-19 | 2019-20 | 2020-21 | 2021-22 | 2022-23 | 2023-24 | 2024-25 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `FILENAMES` | Each release's data files, with their titles and the fields that pick one row | year, fileName | 22 | 575 | 8 (2015-16 to 2022-23) | 68 | 70 | 70 | 70 | 73 | 74 | 74 | 76 |  |  |
| `NEWVARIABLES` | Variables new in each release | year, TableName, VarName | 11 | 110 | 2 (2023-24 to 2024-25) |  |  |  |  |  |  |  |  | 47 | 63 |
| `SECTIONTABLE` | The survey sections of each data file | year, fileName, sectionNumber | 6 | 1,176 | 8 (2015-16 to 2022-23) | 139 | 141 | 144 | 144 | 146 | 152 | 152 | 158 |  |  |
| `TABLES` | Each release's tables: survey, title, years covered and release date | year, TableName | 19 | 508 | 10 (2015-16 to 2024-25) | 47 | 50 | 49 | 50 | 49 | 51 | 52 | 55 | 53 | 52 |
| `TABLES19_RV` | A list of revised tables in the 2019-20 release's codebook; it has no rows | year, TableName | 11 | 0 | 0 |  |  |  |  |  |  |  |  |  |  |
| `VALUESETS` | The codebooks' code labels for every coded variable | year, TableName, varName, Codevalue | 14 | 124,493 | 10 (2015-16 to 2024-25) | 12,382 | 12,712 | 12,468 | 12,749 | 12,495 | 11,890 | 11,593 | 13,038 | 13,023 | 12,143 |
| `VARTABLE` | Every variable of every table, with its title and format | year, TableName, varName | 24 | 23,991 | 10 (2015-16 to 2024-25) | 2,185 | 2,159 | 2,210 | 2,246 | 2,211 | 2,439 | 2,561 | 2,685 | 2,696 | 2,599 |

## Dictionary (16 tables, 6,873 rows)

| Table | What it holds | Key columns | Columns | Rows |
| --- | --- | --- | ---: | ---: |
| `dict_breakdown_exceptions` | Schools whose breakdown is shown despite parts not adding up, by owner decision | breakdown_set, table, year, unitid | 6 | 2 |
| `dict_category_codes` | The category rows of multi-row tables, with labels, defaults and the years each applies | table, column, code | 15 | 1,169 |
| `dict_comparability_breaks` | Definition changes and context notes shown on trends that cross them | kind, tables, first_release | 11 | 14 |
| `dict_concepts` | Reviewed plain-English explanations of IPEDS ideas; the first source for what-does-it-mean questions | concept | 6 | 26 |
| `dict_glossary` | The official IPEDS glossary, 2025-26 edition; used only for what-does-it-mean questions | term | 5 | 612 |
| `dict_group_members` | Groups defined by a list of schools | group, unitid | 3 | 79 |
| `dict_measure_history` | Earlier names of each measure, so a trend continues across a renaming | measure, earlier_table, earlier_variable | 6 | 608 |
| `dict_measures` | Every measure: table, variable, title, unit, period, plain name and set-up status | table, variable | 21 | 3,073 |
| `dict_outside_ipeds` | Topics IPEDS does not collect, and where to look instead | topic | 7 | 16 |
| `dict_rates` | Rates and averages computed from counts: numerator, denominator and method | rate, applies_to | 13 | 28 |
| `dict_school_groups` | Named school groups and how each is defined | group | 14 | 187 |
| `dict_school_nicknames` | Nicknames and abbreviations for schools | nickname | 5 | 36 |
| `dict_special_codes` | How IPEDS's special codes (-1, -2, ...) are read | code | 8 | 36 |
| `dict_terms` | Words people use, their readings and the measures each reading names; settings and messages | term, reading, measure | 15 | 911 |
| `dict_word_abbreviations` | Abbreviated words in school names and what they mean (st: state or saint) | abbreviation, means | 3 | 17 |
| `dict_year_meaning` | What the year of each table means: its period, cohort rule, subject and title | table | 9 | 59 |

## Build result (17 tables, 6,858,764 rows)

| Table | What it holds | Key columns | Columns | Rows |
| --- | --- | --- | ---: | ---: |
| `_missing_reasons` | Why a school has no value in a cell (not applicable, not reported): for display only, never calculated | local_table, year, unitid, column | 6 | 5,095,692 |
| `breakdown_parts` | The parts of each breakdown set | set_name, table, part | 4 | 316 |
| `breakdown_sets` | Tested breakdown sets, per measure, with their total and status (latest year) | set_name, table, measure | 12 | 306 |
| `breakdown_slices` | Breakdown sets tested at other fixed values (a slice) | set_name, table, measure, slice | 7 | 98,295 |
| `detail_link_exceptions` | Schools where a summary and its detailed figure differ, with the reason | measure, unitid | 5 | 133 |
| `detail_links` | Summary measures linked to the detailed table they can be broken down through | measure | 8 | 54 |
| `directory` | One row per school and year: name, location, sector, level, Carnegie and other directory fields | year, UNITID | 36 | 66,957 |
| `group_list` | Every school group the app can use, with its definition and size | group_name | 10 | 4,938 |
| `group_membership` | Which schools belong to each group in each year | group_name, year, unitid | 3 | 1,435,335 |
| `measure_checks` | Measures flagged by the build: never a value, codes without labels, no way to pick one row | measure, check | 3 | 111 |
| `measure_years` | Where each measure is stored in each year, and how many schools have a value | measure, year | 5 | 24,099 |
| `name_clashes` | Shown names still shared by more than one measure | name | 3 | 1 |
| `rate_years` | Whether each rate's counts exist in each year | rate, applies_to, year | 9 | 280 |
| `row_keys` | For each multi-row table, the columns that pick one row and their default codes (latest year) | table, column | 5 | 23 |
| `value_labels` | Code labels for coded columns, from the codebooks, by year | local_table, column, code, year | 5 | 124,440 |
| `year_checks` | Row keys, detail links and breakdown sets tested in every year | year, kind, name, table, measure | 8 | 3,623 |
| `year_titles` | Each measure's title in each year's codebook | measure, year | 3 | 4,161 |

## Housekeeping (7 tables, 30,345 rows)

| Table | What it holds | Key columns | Columns | Rows |
| --- | --- | --- | ---: | ---: |
| `_columns` | Every column loaded from each release, with its types and what cleaning did to it | local_table, release, column | 14 | 25,245 |
| `_conversion_failures` | Values that failed to convert during cleaning (expected to be empty) | local_table, release, column, value | 6 | 0 |
| `_dictionary_state` | Fingerprints of the dictionary files and data, so the fast build knows what changed | item | 2 | 27 |
| `_releases` | The releases loaded, provisional or final, and when | year | 6 | 10 |
| `_special_codes` | The special codes found in each column of each release, and how each was treated | local_table, release, column, code | 10 | 4,439 |
| `_tables` | Every table loaded from each release: source name, kind, rows read and loaded | local_table, year | 10 | 554 |
| `sqlite_stat1` | SQLite's own statistics for its query planner | tbl, idx | 3 | 70 |

Counted in 29 seconds.
