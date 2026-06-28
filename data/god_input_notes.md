# God Input For Constraint Filtering

Use these three files together:

- `data/god_courses.txt`
- `data/god_periods.txt`
- `data/god_programs.txt`

The selected programs are exactly five valid programs, so this sits on the
`MaxProgramsValidator` boundary without failing before scheduling.

What this input stresses:

- Hard program/year conflicts: many obligatory courses share program/year cohorts.
- Moed order: every exam course gets ALEPH and BET slots for its semester.
- Minimum gap, obligatory scope: repeated mandatory cohorts exist in FALL, SPRI, and SUMM.
- Minimum gap, any-course scope: electives share the same program/year cohorts.
- Elective conflict cap: several electives belong to the same program and can land on the same dates.
- Exam span: mandatory groups have multiple courses in the same program/year/semester/moed.
- Max exams per day: enough courses exist across overlapping date windows to create crowded-day branches.
- Non-exam filtering: `PROJECT` and `ATTENDANCE` courses are included and should be ignored by `SlotBuilder`.

Useful CLI runs:

```powershell
python -m src.main data/god_courses.txt data/god_periods.txt data/god_programs.txt --output C:\tmp\god_baseline.txt
```

```powershell
python -m src.main data/god_courses.txt data/god_periods.txt data/god_programs.txt --output C:\tmp\god_all_constraints.txt --min-gap-obligatory 2 --min-gap-any 1 --elective-conflict-cap 3 --exam-span 4 --max-exams-per-day 4
```

```powershell
python -m src.main data/god_courses.txt data/god_periods.txt data/god_programs.txt --output C:\tmp\god_strict.txt --min-gap-obligatory 4 --min-gap-any 3 --elective-conflict-cap 1 --exam-span 7 --max-exams-per-day 2
```

The balanced command above has been smoke-tested with a 5-result limit and
returns schedules. The strict command is useful when you want a very aggressive
pruning run; it may return no schedules depending on the current checker logic.

Expected infeasible/proof runs:

```powershell
python -m src.main data/god_courses.txt data/god_periods.txt data/god_programs.txt --exam-span 10
```

```powershell
python -m src.main data/god_courses.txt data/god_periods.txt data/god_programs.txt --min-gap-obligatory 8
```
