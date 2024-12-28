# scheduler/scheduler.py

from ortools.sat.python import cp_model
from datetime import datetime, timedelta


class ORToolsScheduler:
    def __init__(self, staff_manager, shift_manager, availability_manager):
        self.staff_manager = staff_manager
        self.shift_manager = shift_manager
        self.availability_manager = availability_manager

    def generate_schedule(self, start_date, end_date):
        # 1) Build date list (Mon-Fri only)
        day_list = list(self._date_range(start_date, end_date))

        # (A) Helper: staff specialized if ≤ 3 trained shifts
        def is_specialized_staff(staff_obj):
            return len(staff_obj.trained_shifts) <= 3

        # (B) Fetch shifts & staff
        shifts = self.shift_manager.list_shifts()
        staff_list = self.staff_manager.list_staff()

        # (C) Debug: Which staff can fill each shift on each day?
        print("\n=== Debug: Checking if each shift is fillable per day ===")
        for day in day_list:
            day_str = day.strftime("%Y-%m-%d")
            dow_str = day.strftime("%A")
            week_num = day.isocalendar()[1]
            print(f"DEBUG: Processing {day_str} ({dow_str}, Week {week_num})")

            # If holiday => no staff
            if self.availability_manager.is_holiday(day_str):
                print(f"  {day_str}, HOLIDAY => forced sum(...)=0 for all shifts.")
                continue

            for shift in shifts:
                can_remain_open = getattr(shift, 'can_remain_open', False)
                shift_type = "Optional" if can_remain_open else "Mandatory"
                valid_staff = []
                for staff in staff_list:
                    if self.availability_manager.is_available(staff.initials, day_str):
                        role_match = (shift.role_required == "Any" or shift.role_required == staff.role)
                        skill_match = (shift.name == "Any" or shift.name in staff.trained_shifts)
                        if role_match and skill_match:
                            valid_staff.append(staff.initials)
                        else:
                            print(f"    DEBUG: {staff.initials} => "
                                  f"(Role Match={role_match}, Skill Match={skill_match}) for shift '{shift.name}'")
                if valid_staff:
                    print(f"  -> {day_str}, Shift={shift.name} ({shift_type}) -> Fillable by: {valid_staff}")
                else:
                    print(f"  -> {day_str}, Shift={shift.name} ({shift_type}) -> No staff can fill this!")

        # (D) Debug: staff listing
        print("\n=== Debug: Staff List and Trained Shifts ===")
        for s in staff_list:
            print(f"Staff: {s.initials}, Role: {s.role}, "
                  f"Trained Shifts: {s.trained_shifts}, Is Casual: {s.is_casual}")

        # (E) Create the CP-SAT model
        model = cp_model.CpModel()

        # (F) Decision variables: assign[(d, s, e)] => staff e on shift s day d
        assign = {}
        for d, day in enumerate(day_list):
            for s, shift in enumerate(shifts):
                for e, staff in enumerate(staff_list):
                    assign[(d, s, e)] = model.NewBoolVar(f"assign_day{d}_shift{s}_emp{e}")

        # Track unfilled optional shifts (for penalty).
        unfilled_opt_vars = []

        # (G) Day-of-week + shift rules (Mandatory vs. Optional)
        print("\n=== Debug: Building day/shift constraints based on days_of_week ===")
        for d, day in enumerate(day_list):
            day_str = day.strftime("%Y-%m-%d")

            for s, shift_obj in enumerate(shifts):
                day_name = day.strftime("%A")
                if day_name not in shift_obj.days_of_week:
                    # Shift doesn't run that day => sum(...)=0
                    print(f"  -> {day_str}, Shift '{shift_obj.name}' not running -> forced sum(...)=0")
                    model.Add(sum(assign[(d, s, e)] for e in range(len(staff_list))) == 0)
                    continue

                if self.availability_manager.is_holiday(day_str):
                    print(f"  -> {day_str}, Shift '{shift_obj.name}' => HOLIDAY => forced sum(...)=0")
                    model.Add(sum(assign[(d, s, e)] for e in range(len(staff_list))) == 0)
                    continue

                if getattr(shift_obj, 'can_remain_open', False):
                    # Optional => sum(...) ≤ 1
                    print(f"  -> {day_str}, Shift '{shift_obj.name}' is optional -> forced sum(...)<=1")
                    sum_assignments = sum(assign[(d, s, e)] for e in range(len(staff_list)))
                    model.Add(sum_assignments <= 1)

                    # Track if optional shift is left unfilled
                    unfilled_opt_var = model.NewBoolVar(f"unfilled_opt_d{d}_s{s}")
                    model.Add(sum_assignments == 0).OnlyEnforceIf(unfilled_opt_var)
                    model.Add(sum_assignments > 0).OnlyEnforceIf(unfilled_opt_var.Not())
                    unfilled_opt_vars.append(unfilled_opt_var)

                else:
                    # Mandatory => sum(...) == 1
                    print(f"  -> {day_str}, Shift '{shift_obj.name}' is mandatory -> forced sum(...)=1")
                    model.Add(sum(assign[(d, s, e)] for e in range(len(staff_list))) == 1)

        # (H) No staff can do more than 1 shift in a single day
        for d, day in enumerate(day_list):
            for e in range(len(staff_list)):
                model.Add(sum(assign[(d, s, e)] for s in range(len(shifts))) <= 1)

        # (I) Enforce availability, role, skill
        week_map = [day.isocalendar()[1] for day in day_list]
        unique_weeks = sorted(set(week_map))
        print(f"\nDEBUG: Unique weeks identified: {unique_weeks}")

        for d, day in enumerate(day_list):
            day_str = day.strftime("%Y-%m-%d")
            if self.availability_manager.is_holiday(day_str):
                for s in range(len(shifts)):
                    for e in range(len(staff_list)):
                        model.Add(assign[(d, s, e)] == 0)
            else:
                for s, shift_obj in enumerate(shifts):
                    if day.strftime("%A") not in shift_obj.days_of_week:
                        continue
                    for e, staff in enumerate(staff_list):
                        if not self.availability_manager.is_available(staff.initials, day_str):
                            model.Add(assign[(d, s, e)] == 0)
                        elif shift_obj.role_required != "Any" and shift_obj.role_required != staff.role:
                            model.Add(assign[(d, s, e)] == 0)
                        elif shift_obj.name != "Any" and (shift_obj.name not in staff.trained_shifts):
                            model.Add(assign[(d, s, e)] == 0)

        # (J) Limit staff to at most 1 “Cyto UTD” per week & 1 “Cyto UTD IMG” per week
        SHIFT_UTD = "Cyto UTD"
        SHIFT_UTD_IMG = "Cyto UTD IMG"

        for e, staff in enumerate(staff_list):
            for w in unique_weeks:
                utd_assigns = []
                utd_img_assigns = []
                for d, day in enumerate(day_list):
                    if week_map[d] == w:
                        for s, shift_obj in enumerate(shifts):
                            if shift_obj.name == SHIFT_UTD:
                                utd_assigns.append(assign[(d, s, e)])
                            if shift_obj.name == SHIFT_UTD_IMG:
                                utd_img_assigns.append(assign[(d, s, e)])
                if utd_assigns:
                    model.Add(sum(utd_assigns) <= 1)
                if utd_img_assigns:
                    model.Add(sum(utd_img_assigns) <= 1)

        # (K) Weekly maximum shifts = 5
        MAX_SHIFTS_PER_WEEK = 5
        over_shift_vars = []
        for e, staff in enumerate(staff_list):
            for w in unique_weeks:
                shifts_assigned_this_week = [
                    assign[(d, s, e)]
                    for d, day in enumerate(day_list) if week_map[d] == w
                    for s in range(len(shifts))
                ]
                if not shifts_assigned_this_week:
                    continue

                shifts_assigned_var = model.NewIntVar(
                    0, len(shifts_assigned_this_week),
                    f"shifts_e{e}_w{w}"
                )
                model.Add(shifts_assigned_var == sum(shifts_assigned_this_week))

                over_shifts = model.NewIntVar(
                    0, len(shifts_assigned_this_week),
                    f"over_shifts_e{e}_w{w}"
                )
                model.Add(over_shifts >= shifts_assigned_var - MAX_SHIFTS_PER_WEEK)
                model.Add(over_shifts >= 0)
                over_shift_vars.append(over_shifts)

        # (L) Fairness objective: minimize (max_shifts - min_shifts)
        total_shifts_per_emp = []
        for e in range(len(staff_list)):
            var = model.NewIntVar(0, len(day_list) * len(shifts), f"total_shifts_{e}")
            model.Add(var == sum(assign[(d, s, e)]
                                 for d in range(len(day_list))
                                 for s in range(len(shifts))))
            total_shifts_per_emp.append(var)

        max_shifts = model.NewIntVar(0, len(day_list) * len(shifts), "max_shifts")
        min_shifts = model.NewIntVar(0, len(day_list) * len(shifts), "min_shifts")
        for e in range(len(staff_list)):
            model.Add(total_shifts_per_emp[e] <= max_shifts)
            model.Add(total_shifts_per_emp[e] >= min_shifts)
        diff = model.NewIntVar(0, len(day_list) * len(shifts), "diff")
        model.Add(diff == max_shifts - min_shifts)

        # (M) Casual usage penalty
        casual_cost_vars = []
        for d, day in enumerate(day_list):
            for s, shift in enumerate(shifts):
                for e, staff in enumerate(staff_list):
                    c_var = model.NewIntVar(0, 1, f"casual_cost_d{d}_s{s}_e{e}")
                    if getattr(staff, 'is_casual', False):
                        model.Add(c_var == assign[(d, s, e)])
                    else:
                        model.Add(c_var == 0)
                    casual_cost_vars.append(c_var)
        total_casual_usage = model.NewIntVar(0, len(day_list) * len(shifts), "total_casual_usage")
        model.Add(total_casual_usage == sum(casual_cost_vars))

        # (N) Variety penalty: staff with >3 trained shifts => penalize shift repeats
        SHIFT_REPEATS_MAX = 1
        SHIFT_REPEATS_PENALTY = 10
        repeat_penalty_vars = []
        for e, staff in enumerate(staff_list):
            if not is_specialized_staff(staff):
                for w in unique_weeks:
                    for s, shift_obj in enumerate(shifts):
                        assigned_this_shift_week = []
                        for d, day in enumerate(day_list):
                            if week_map[d] == w:
                                assigned_this_shift_week.append(assign[(d, s, e)])
                        if assigned_this_shift_week:
                            shift_sum_var = model.NewIntVar(0, len(assigned_this_shift_week),
                                                            f"shift_sum_e{e}_s{s}_w{w}")
                            model.Add(shift_sum_var == sum(assigned_this_shift_week))

                            repeated_var = model.NewIntVar(0, len(assigned_this_shift_week),
                                                           f"repeated_var_e{e}_s{s}_w{w}")
                            model.Add(repeated_var >= shift_sum_var - SHIFT_REPEATS_MAX)
                            model.Add(repeated_var >= 0)
                            repeat_penalty_vars.append(repeated_var)

        # (N.2) DS must be scheduled exactly 2 times per week on MCY
        SHIFT_MCY = "Cyto MCY"
        ds_index = None
        mcy_index = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_MCY:
                mcy_index = s_i
                break
        for e_i, staff_obj in enumerate(staff_list):
            if staff_obj.initials == "DS":
                ds_index = e_i
                break
        if ds_index is not None and mcy_index is not None:
            for w in unique_weeks:
                ds_mcy_assigns = []
                for d, day in enumerate(day_list):
                    if week_map[d] == w:
                        ds_mcy_assigns.append(assign[(d, mcy_index, ds_index)])
                # EXACT 2 times per week
                if ds_mcy_assigns:
                    model.Add(sum(ds_mcy_assigns) == 2)

        # (N.4) Penalty for scheduling a Cytologist on Cyto FNA or EUS >1 time/week
        SHIFT_FNA = "Cyto FNA"
        SHIFT_EUS = "Cyto EUS"
        FNA_EUS_PENALTY = 8  # penalty per extra assignment

        fna_eus_penalty_vars = []
        fna_idx = None
        eus_idx = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_FNA:
                fna_idx = s_i
            elif shf.name == SHIFT_EUS:
                eus_idx = s_i

        for e, staff in enumerate(staff_list):
            if staff.role == "Cytologist":
                for w in unique_weeks:
                    if fna_idx is not None:
                        fna_assigns = []
                    else:
                        fna_assigns = None

                    if eus_idx is not None:
                        eus_assigns = []
                    else:
                        eus_assigns = None

                    for d, day in enumerate(day_list):
                        if week_map[d] == w:
                            if fna_assigns is not None:
                                fna_assigns.append(assign[(d, fna_idx, e)])
                            if eus_assigns is not None:
                                eus_assigns.append(assign[(d, eus_idx, e)])

                    # Penalty if >1 assignment to FNA
                    if fna_assigns:
                        sum_fna = model.NewIntVar(0, len(fna_assigns), f"sum_fna_e{e}_w{w}")
                        model.Add(sum_fna == sum(fna_assigns))

                        penalty_fna = model.NewIntVar(0, len(fna_assigns), f"penalty_fna_e{e}_w{w}")
                        model.Add(penalty_fna >= sum_fna - 1)
                        model.Add(penalty_fna >= 0)
                        fna_eus_penalty_vars.append(penalty_fna)

                    # Penalty if >1 assignment to EUS
                    if eus_assigns:
                        sum_eus = model.NewIntVar(0, len(eus_assigns), f"sum_eus_e{e}_w{w}")
                        model.Add(sum_eus == sum(eus_assigns))

                        penalty_eus = model.NewIntVar(0, len(eus_assigns), f"penalty_eus_e{e}_w{w}")
                        model.Add(penalty_eus >= sum_eus - 1)
                        model.Add(penalty_eus >= 0)
                        fna_eus_penalty_vars.append(penalty_eus)

        # (N.5) No back-to-back days for Cyto EUS and Cyto FNA
        # i.e. a single staff can't be on EUS or FNA on day d and again on day d+1
        SHIFT_EUS = "Cyto EUS"
        SHIFT_FNA = "Cyto FNA"

        # Identify shift indices for EUS and FNA, if they exist
        eus_idx = None
        fna_idx = None
        for s_i, shift_obj in enumerate(shifts):
            if shift_obj.name == SHIFT_EUS:
                eus_idx = s_i
            elif shift_obj.name == SHIFT_FNA:
                fna_idx = s_i

        if eus_idx is not None and fna_idx is not None:
            # For each staff, for each consecutive pair of days
            for e, staff in enumerate(staff_list):
                for d in range(len(day_list) - 1):
                    # EUS or FNA on day d?
                    day_d_vars = []
                    day_d_vars.append(assign[(d, eus_idx, e)])
                    day_d_vars.append(assign[(d, fna_idx, e)])
                    sum_day_d = model.NewIntVar(0, 2, f"sum_day{d}_heavy_e{e}")
                    model.Add(sum_day_d == sum(day_d_vars))

                    # EUS or FNA on day d+1?
                    day_dplus1_vars = []
                    day_dplus1_vars.append(assign[(d + 1, eus_idx, e)])
                    day_dplus1_vars.append(assign[(d + 1, fna_idx, e)])
                    sum_day_dplus1 = model.NewIntVar(0, 2, f"sum_day{d+1}_heavy_e{e}")
                    model.Add(sum_day_dplus1 == sum(day_dplus1_vars))

                    # Disallow staff from working EUS/FNA on back-to-back days
                    # => sum_day_d + sum_day_dplus1 <= 1
                    model.Add(sum_day_d + sum_day_dplus1 <= 1)


        # (N.6) KL’s preferences (EBUS×2, Clerical×1, GYN×1)
        SHIFT_EBUS = "Prep EBUS"
        SHIFT_CLERICAL = "Prep Clerical"
        SHIFT_GYN = "Prep GYN"

        KL_MIN_EBUS = 2
        KL_MIN_CLERICAL = 1
        KL_MIN_GYN = 1

        KL_PENALTY_EBUS = 5
        KL_PENALTY_CLERICAL = 5
        KL_PENALTY_GYN = 5

        # Find shift indices for EBUS, Clerical, GYN
        ebus_index = None
        clerical_index = None
        gyn_index = None
        for s_i, shift_obj in enumerate(shifts):
            if shift_obj.name == SHIFT_EBUS:
                ebus_index = s_i
            elif shift_obj.name == SHIFT_CLERICAL:
                clerical_index = s_i
            elif shift_obj.name == SHIFT_GYN:
                gyn_index = s_i

        # Identify KL’s staff index
        kl_index = None
        for e_i, staff_obj in enumerate(staff_list):
            if staff_obj.initials == "KL":
                kl_index = e_i
                break

        kl_shortfall_vars = []
        if kl_index is not None:
            for w in unique_weeks:
                ebus_assigns = []
                clerical_assigns = []
                gyn_assigns = []

                for d, day in enumerate(day_list):
                    if week_map[d] == w:
                        if ebus_index is not None:
                            ebus_assigns.append(assign[(d, ebus_index, kl_index)])
                        if clerical_index is not None:
                            clerical_assigns.append(assign[(d, clerical_index, kl_index)])
                        if gyn_index is not None:
                            gyn_assigns.append(assign[(d, gyn_index, kl_index)])

                # EBUS shortfall
                if ebus_assigns:
                    sum_ebus = model.NewIntVar(0, len(ebus_assigns), f"kl_ebus_sum_w{w}")
                    model.Add(sum_ebus == sum(ebus_assigns))

                    shortfall_ebus = model.NewIntVar(0, KL_MIN_EBUS, f"shortfall_ebus_w{w}")
                    model.Add(shortfall_ebus >= KL_MIN_EBUS - sum_ebus)
                    model.Add(shortfall_ebus >= 0)
                    kl_shortfall_vars.append((shortfall_ebus, KL_PENALTY_EBUS))

                # Clerical shortfall
                if clerical_assigns:
                    sum_clerical = model.NewIntVar(0, len(clerical_assigns), f"kl_clerical_sum_w{w}")
                    model.Add(sum_clerical == sum(clerical_assigns))

                    shortfall_clerical = model.NewIntVar(0, KL_MIN_CLERICAL, f"shortfall_clerical_w{w}")
                    model.Add(shortfall_clerical >= KL_MIN_CLERICAL - sum_clerical)
                    model.Add(shortfall_clerical >= 0)
                    kl_shortfall_vars.append((shortfall_clerical, KL_PENALTY_CLERICAL))

                # GYN shortfall
                if gyn_assigns:
                    sum_gyn = model.NewIntVar(0, len(gyn_assigns), f"kl_gyn_sum_w{w}")
                    model.Add(sum_gyn == sum(gyn_assigns))

                    shortfall_gyn = model.NewIntVar(0, KL_MIN_GYN, f"shortfall_gyn_w{w}")
                    model.Add(shortfall_gyn >= KL_MIN_GYN - sum_gyn)
                    model.Add(shortfall_gyn >= 0)
                    kl_shortfall_vars.append((shortfall_gyn, KL_PENALTY_GYN))

        # Build an expression for KL preference shortfalls
        kl_preference_penalties = []
        for (sf_var, penalty_val) in kl_shortfall_vars:
            kl_preference_penalties.append(sf_var * penalty_val)

        # (O) Weighted objective
        WeightedObjective = model.NewIntVar(0, 999999, "WeightedObjective")

        variety_sum = sum(repeat_penalty_vars) if repeat_penalty_vars else 0
        UNFILLED_OPT_PENALTY = 5

        # Summation expression for FNA/EUS penalty
        FNA_EUS_PENALTY = 8  # (already used above)

        # Now combine everything:
        model.Add(
            WeightedObjective
            == diff
            + 10 * total_casual_usage
            + SHIFT_REPEATS_PENALTY * variety_sum
            + UNFILLED_OPT_PENALTY * sum(unfilled_opt_vars)
            + FNA_EUS_PENALTY * sum(fna_eus_penalty_vars)
            # KL preferences:
            + sum(kl_preference_penalties)
        )

        model.Minimize(WeightedObjective)

        # (P) Solve
        solver = cp_model.CpSolver()
        solver.parameters.log_search_progress = True
        print("\n=== Debug: Solving CP model... ===\n")
        status = solver.Solve(model)

        final_schedule = {}
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print("\n=== Debug: Schedule Assignments ===")
            for d, day in enumerate(day_list):
                day_str = day.strftime("%Y-%m-%d")
                final_schedule[day_str] = []
                for s, shift_obj in enumerate(shifts):
                    if day.strftime("%A") not in shift_obj.days_of_week:
                        continue

                    assigned_emp = "Unassigned"
                    for e, staff in enumerate(staff_list):
                        if solver.Value(assign[(d, s, e)]) == 1:
                            assigned_emp = staff.initials
                            # Double-check training
                            if shift_obj.name not in staff.trained_shifts and shift_obj.name != "Any":
                                print(f"ERROR: {staff.initials} => untrained '{shift_obj.name}' on {day_str}")
                            else:
                                print(f"DEBUG: {day_str}, Shift '{shift_obj.name}' => {staff.initials}")
                            break

                    final_schedule[day_str].append({
                        'shift': shift_obj.name,
                        'assigned_to': assigned_emp,
                        'role': shift_obj.role_required,
                        'is_flexible': getattr(shift_obj, 'is_flexible', False),
                        'can_remain_open': getattr(shift_obj, 'can_remain_open', False),
                    })

            # Debug any "over shift" usage
            print("\n=== Debug: Over-Shift (no penalty) ===")
            for over_var in over_shift_vars:
                over_count = solver.Value(over_var)
                if over_count > 0:
                    print(f"Over shift limit by {over_count} for some staff/week.")
        else:
            print("No feasible solution found.")

        return final_schedule

    def _date_range(self, start_str, end_str):
        """
        Convert date strings to a list of date objects,
        skipping weekends (only Monday–Friday).
        """
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        delta = timedelta(days=1)

        date_list = []
        while start <= end:
            if start.weekday() < 5:  # Monday=0..Friday=4
                date_list.append(start)
            start += delta
        return date_list
