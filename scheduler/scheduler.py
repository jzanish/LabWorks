# scheduler/scheduler.py

import os
import json
from ortools.sat.python import cp_model
from datetime import datetime, timedelta

# Dictionary with day-of-week -> shift -> effort
EFFORT_MAP = {
    "Monday": {
        "Cyto Nons 1": 5,
        "Cyto Nons 2": 5,
        "Cyto FNA": 8,
        "Cyto EUS": 10,
        "Cyto FLOAT": 6,
        "Cyto 2ND (1)": 5,
        "Cyto 2ND (2)": 5,
        "Cyto IMG": 4,
        "Cyto APERIO": 4,
        "Cyto MCY": 7,
        "Cyto UTD": 10,
        "Cyto UTD IMG": 7,
        "Prep AM Nons": 10,
        "Prep GYN": 7,
        "Prep EBUS": 7,
        "Prep FNA": 7,
        "Prep NONS 1": 10,
        "Prep NONS 2": 8,
        "Prep Clerical": 7,
    },
    "Tuesday": {
        "Cyto Nons 1": 5,
        "Cyto Nons 2": 5,
        "Cyto FNA": 8,
        "Cyto EUS": 10,
        "Cyto FLOAT": 6,
        "Cyto 2ND (1)": 5,
        "Cyto 2ND (2)": 5,
        "Cyto IMG": 4,
        "Cyto APERIO": 4,
        "Cyto MCY": 7,
        "Cyto UTD": 8,
        "Cyto UTD IMG": 5,
        "Prep AM Nons": 10,
        "Prep GYN": 7,
        "Prep EBUS": 7,
        "Prep FNA": 7,
        "Prep NONS 1": 10,
        "Prep NONS 2": 8,
        "Prep Clerical": 7,
    },
    "Wednesday": {
        "Cyto Nons 1": 5,
        "Cyto Nons 2": 5,
        "Cyto FNA": 8,
        "Cyto EUS": 10,
        "Cyto FLOAT": 6,
        "Cyto 2ND (1)": 5,
        "Cyto 2ND (2)": 5,
        "Cyto IMG": 4,
        "Cyto APERIO": 4,
        "Cyto MCY": 7,
        "Cyto UTD": 8,
        "Cyto UTD IMG": 5,
        "Prep AM Nons": 10,
        "Prep GYN": 7,
        "Prep EBUS": 7,
        "Prep FNA": 7,
        "Prep NONS 1": 10,
        "Prep NONS 2": 8,
        "Prep Clerical": 7,
    },
    "Thursday": {
        "Cyto Nons 1": 5,
        "Cyto Nons 2": 5,
        "Cyto FNA": 8,
        "Cyto EUS": 10,
        "Cyto FLOAT": 6,
        "Cyto 2ND (1)": 5,
        "Cyto 2ND (2)": 5,
        "Cyto IMG": 4,
        "Cyto APERIO": 4,
        "Cyto MCY": 7,
        "Cyto UTD": 8,
        "Cyto UTD IMG": 5,
        "Prep AM Nons": 10,
        "Prep GYN": 7,
        "Prep EBUS": 7,
        "Prep FNA": 7,
        "Prep NONS 1": 10,
        "Prep NONS 2": 8,
        "Prep Clerical": 7,
    },
    "EBUS Friday": {
        "Cyto Nons 1": 5,
        "Cyto Nons 2": 5,
        "Cyto FNA": 8,
        "Cyto EUS": 10,
        "Cyto FLOAT": 6,
        "Cyto 2ND (1)": 5,
        "Cyto 2ND (2)": 5,
        "Cyto IMG": 4,
        "Cyto APERIO": 4,
        "Cyto MCY": 7,
        "Cyto UTD": 10,
        "Cyto UTD IMG": 7,
        "Prep AM Nons": 10,
        "Prep GYN": 7,
        "Prep EBUS": 7,
        "Prep FNA": 7,
        "Prep NONS 1": 10,
        "Prep NONS 2": 8,
        "Prep Clerical": 7,
    },
    "Regular Friday": {
        "Cyto Nons 1": 5,
        "Cyto Nons 2": 5,
        "Cyto FNA": 8,
        "Cyto EUS": 10,
        "Cyto FLOAT": 6,
        "Cyto 2ND (1)": 5,
        "Cyto 2ND (2)": 5,
        "Cyto IMG": 4,
        "Cyto APERIO": 4,
        "Cyto MCY": 7,
        "Cyto UTD": 8,
        "Cyto UTD IMG": 5,
        "Prep AM Nons": 10,
        "Prep GYN": 7,
        "Prep EBUS": 7,
        "Prep FNA": 7,
        "Prep NONS 1": 10,
        "Prep NONS 2": 8,
        "Prep Clerical": 7,
    },
}
DEFAULT_EFFORT = 5  # fallback if not found in EFFORT_MAP


class ORToolsScheduler:
    def __init__(self, staff_manager, shift_manager, availability_manager):
        self.staff_manager = staff_manager
        self.shift_manager = shift_manager
        self.availability_manager = availability_manager

    def generate_schedule(self, start_date, end_date, preassigned=None, is_ebus_friday=False):
        """
        Generates a schedule with your custom constraints, manual picks, shift count fairness,
        day/shift-based effort fairness for staff with >3 trained shifts, no back-to-back
        for FNA/EUS/UTD/MCY, and a soft preference for 'Cyto Nons 2' over 'Cyto IMG'.

        If is_ebus_friday=True, any Friday in the date range uses "EBUS Friday" from EFFORT_MAP;
        otherwise, it uses "Regular Friday".
        """

        if preassigned is None:
            preassigned = {}

        # 1) Build date list (Mon-Fri only)
        day_list = list(self._date_range(start_date, end_date))

        def is_specialized_staff(staff_obj):
            return len(staff_obj.trained_shifts) <= 3

        shifts = self.shift_manager.list_shifts()
        staff_list = self.staff_manager.list_staff()

        print("\n=== Debug: Checking fillable shifts/day ===")
        for day in day_list:
            day_str = day.strftime("%Y-%m-%d")
            dow_str = day.strftime("%A")
            print(f"DEBUG: Processing {day_str} ({dow_str})")

            if self.availability_manager.is_holiday(day_str):
                print(f"  -> {day_str}, HOLIDAY => sum(...)=0 for all shifts.")
                continue

            for shift in shifts:
                can_remain_open = getattr(shift, 'can_remain_open', False)
                shift_type = "Optional" if can_remain_open else "Mandatory"

                valid_staff = []
                for stf in staff_list:
                    # If forced assignment => skip normal checks
                    if (day_str, shift.name) in preassigned and preassigned[(day_str, shift.name)] == stf.initials:
                        valid_staff.append(stf.initials)
                    else:
                        if self.availability_manager.is_available(stf.initials, day_str):
                            role_match = (shift.role_required == "Any" or shift.role_required == stf.role)
                            skill_match = (shift.name == "Any" or shift.name in stf.trained_shifts)
                            if role_match and skill_match:
                                valid_staff.append(stf.initials)

                if valid_staff:
                    print(f"  -> {day_str}, shift={shift.name} ({shift_type}) => {valid_staff}")
                else:
                    print(f"  -> {day_str}, shift={shift.name} ({shift_type}) => NO staff can fill")

        # Create CP model
        model = cp_model.CpModel()

        # (F) Decision variables: assign[(d, s, e)]
        assign = {}
        for d, day in enumerate(day_list):
            for s, shift_obj in enumerate(shifts):
                for e, stf in enumerate(staff_list):
                    assign[(d, s, e)] = model.NewBoolVar(f"assign_d{d}_s{s}_e{e}")

        unfilled_opt_vars = []
        day_to_idx = {day_list[i].strftime("%Y-%m-%d"): i for i in range(len(day_list))}
        shiftname_to_idx = {shifts[s_i].name: s_i for s_i in range(len(shifts))}
        staff_init_to_idx = {staff_list[e_i].initials: e_i for e_i in range(len(staff_list))}

        # (G) Mandatory vs Optional
        for d, day in enumerate(day_list):
            day_str = day.strftime("%Y-%m-%d")
            day_name = day.strftime("%A")

            for s, shift_obj in enumerate(shifts):
                if (day_str, shift_obj.name) in preassigned:
                    continue

                if day_name not in shift_obj.days_of_week:
                    model.Add(sum(assign[(d, s, e)] for e in range(len(staff_list))) == 0)
                    continue

                if self.availability_manager.is_holiday(day_str):
                    model.Add(sum(assign[(d, s, e)] for e in range(len(staff_list))) == 0)
                    continue

                if getattr(shift_obj, 'can_remain_open', False):
                    sum_assign = sum(assign[(d, s, e)] for e in range(len(staff_list)))
                    model.Add(sum_assign <= 1)
                    var_opt = model.NewBoolVar(f"unfilled_opt_d{d}_s{s}")
                    model.Add(sum_assign == 0).OnlyEnforceIf(var_opt)
                    model.Add(sum_assign > 0).OnlyEnforceIf(var_opt.Not())
                    unfilled_opt_vars.append(var_opt)
                else:
                    model.Add(sum(assign[(d, s, e)] for e in range(len(staff_list))) == 1)

        # (H) No staff more than 1 shift in same day
        for d in range(len(day_list)):
            for e in range(len(staff_list)):
                model.Add(sum(assign[(d, s, e)] for s in range(len(shifts))) <= 1)

        # (I) Skip normal checks if forced
        week_map = [day.isocalendar()[1] for day in day_list]
        unique_weeks = sorted(set(week_map))

        for d, day in enumerate(day_list):
            day_str = day.strftime("%Y-%m-%d")
            if self.availability_manager.is_holiday(day_str):
                for s, shf in enumerate(shifts):
                    if (day_str, shf.name) in preassigned:
                        continue
                    for e in range(len(staff_list)):
                        model.Add(assign[(d, s, e)] == 0)
            else:
                for s, shf in enumerate(shifts):
                    if (day_str, shf.name) in preassigned:
                        continue
                    if day.strftime("%A") not in shf.days_of_week:
                        continue
                    for e, stf in enumerate(staff_list):
                        if not self.availability_manager.is_available(stf.initials, day_str):
                            model.Add(assign[(d, s, e)] == 0)
                        elif shf.role_required != "Any" and shf.role_required != stf.role:
                            model.Add(assign[(d, s, e)] == 0)
                        elif shf.name != "Any" and (shf.name not in stf.trained_shifts):
                            model.Add(assign[(d, s, e)] == 0)

        # (J) Limit staff to at most 1 "Cyto UTD" & 1 "Cyto UTD IMG" per week
        SHIFT_UTD = "Cyto UTD"
        SHIFT_UTD_IMG = "Cyto UTD IMG"
        for e, stf in enumerate(staff_list):
            for w in unique_weeks:
                utd_bools = []
                utd_img_bools = []
                for d, day in enumerate(day_list):
                    if week_map[d] == w:
                        for s, shf in enumerate(shifts):
                            if shf.name == SHIFT_UTD:
                                utd_bools.append(assign[(d, s, e)])
                            elif shf.name == SHIFT_UTD_IMG:
                                utd_img_bools.append(assign[(d, s, e)])
                if utd_bools:
                    model.Add(sum(utd_bools) <= 1)
                if utd_img_bools:
                    model.Add(sum(utd_img_bools) <= 1)

        # (K) Weekly max=5
        MAX_PER_WEEK = 5
        over_shift_vars = []
        for e, stf in enumerate(staff_list):
            for w in unique_weeks:
                bools_week = [
                    assign[(d, s, e)]
                    for d in range(len(day_list)) if week_map[d] == w
                    for s in range(len(shifts))
                ]
                if not bools_week:
                    continue
                sum_var = model.NewIntVar(0, len(bools_week), f"sum_e{e}_w{w}")
                model.Add(sum_var == sum(bools_week))

                overvar = model.NewIntVar(0, len(bools_week), f"over_e{e}_w{w}")
                model.Add(overvar >= sum_var - MAX_PER_WEEK)
                model.Add(overvar >= 0)
                over_shift_vars.append(overvar)

        # (L) SHIFT-COUNT fairness => define diff
        total_shifts_per_emp = []
        for e in range(len(staff_list)):
            var = model.NewIntVar(0, len(day_list) * len(shifts), f"tot_shifts_{e}")
            model.Add(var == sum(assign[(d, s, e)]
                                 for d in range(len(day_list))
                                 for s in range(len(shifts))))
            total_shifts_per_emp.append(var)

        max_shifts = model.NewIntVar(0, len(day_list)*len(shifts), "max_shifts")
        min_shifts = model.NewIntVar(0, len(day_list)*len(shifts), "min_shifts")
        for e in range(len(staff_list)):
            model.Add(total_shifts_per_emp[e] <= max_shifts)
            model.Add(total_shifts_per_emp[e] >= min_shifts)
        diff = model.NewIntVar(0, len(day_list)*len(shifts), "diff")
        model.Add(diff == max_shifts - min_shifts)

        # (M) Casual usage penalty
        casual_vars = []
        for d in range(len(day_list)):
            for s in range(len(shifts)):
                for e, stf in enumerate(staff_list):
                    c_var = model.NewIntVar(0, 1, f"casual_d{d}_s{s}_e{e}")
                    if stf.is_casual:
                        model.Add(c_var == assign[(d, s, e)])
                    else:
                        model.Add(c_var == 0)
                    casual_vars.append(c_var)
        total_casual_usage = model.NewIntVar(0, len(day_list)*len(shifts), "tot_casual")
        model.Add(total_casual_usage == sum(casual_vars))

        # (N) Variety penalty: staff w/ >3 trained => SHIFT_REPEATS_MAX=1
        SHIFT_REPEATS_MAX = 1
        SHIFT_REPEATS_PENALTY = 10
        repeat_penalty_vars = []
        for e, stf in enumerate(staff_list):
            if not is_specialized_staff(stf):
                for w in unique_weeks:
                    for s, shf_obj in enumerate(shifts):
                        bools_this_week_shift = []
                        for d, day in enumerate(day_list):
                            if week_map[d] == w:
                                bools_this_week_shift.append(assign[(d, s, e)])
                        if bools_this_week_shift:
                            sum_var = model.NewIntVar(0, len(bools_this_week_shift),
                                                      f"sum_e{e}_s{s}_w{w}")
                            model.Add(sum_var == sum(bools_this_week_shift))

                            repeated_var = model.NewIntVar(0, len(bools_this_week_shift),
                                                           f"rep_e{e}_s{s}_w{w}")
                            model.Add(repeated_var >= sum_var - SHIFT_REPEATS_MAX)
                            model.Add(repeated_var >= 0)
                            repeat_penalty_vars.append(repeated_var)

        # (N.2) DS must be scheduled exactly 2 times/wk on MCY
        SHIFT_MCY = "Cyto MCY"
        ds_index = None
        mcy_index = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_MCY:
                mcy_index = s_i
        for e_i, stf in enumerate(staff_list):
            if stf.initials == "DS":
                ds_idx = e_i
        if ds_idx is not None and mcy_index is not None:
            for w in unique_weeks:
                ds_vars = []
                for d, day in enumerate(day_list):
                    if week_map[d] == w:
                        ds_vars.append(assign[(d, mcy_index, ds_idx)])
                model.Add(sum(ds_vars) == 2)

        # (N.4) Cytologist FNA/EUS penalty
        SHIFT_FNA = "Cyto FNA"
        SHIFT_EUS = "Cyto EUS"
        FNA_EUS_PENALTY = 8

        fna_idx = None
        eus_idx = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_FNA:
                fna_idx = s_i
            elif shf.name == SHIFT_EUS:
                eus_idx = s_i

        fna_eus_penalty_vars = []
        for e, stf in enumerate(staff_list):
            if stf.role == "Cytologist":
                for w in unique_weeks:
                    fna_dayvars = []
                    eus_dayvars = []
                    for d, day in enumerate(day_list):
                        if week_map[d] == w:
                            if fna_idx is not None:
                                fna_dayvars.append(assign[(d, fna_idx, e)])
                            if eus_idx is not None:
                                eus_dayvars.append(assign[(d, eus_idx, e)])
                    if fna_dayvars:
                        sum_fna = model.NewIntVar(0, len(fna_dayvars), f"sum_fna_e{e}_w{w}")
                        model.Add(sum_fna == sum(fna_dayvars))
                        pen_fna = model.NewIntVar(0, len(fna_dayvars), f"pen_fna_e{e}_w{w}")
                        model.Add(pen_fna >= sum_fna - 1)
                        model.Add(pen_fna >= 0)
                        fna_eus_penalty_vars.append(pen_fna)

                    if eus_dayvars:
                        sum_eus = model.NewIntVar(0, len(eus_dayvars), f"sum_eus_e{e}_w{w}")
                        model.Add(sum_eus == sum(eus_dayvars))
                        pen_eus = model.NewIntVar(0, len(eus_dayvars), f"pen_eus_e{e}_w{w}")
                        model.Add(pen_eus >= sum_eus - 1)
                        model.Add(pen_eus >= 0)
                        fna_eus_penalty_vars.append(pen_eus)

        # >>> No back-to-back for EUS, FNA, UTD, MCY
        SHIFT_UTD = "Cyto UTD"
        new_eus_idx = None
        new_fna_idx = None
        new_utd_idx = None
        new_mcy_idx = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_EUS:
                new_eus_idx = s_i
            elif shf.name == SHIFT_FNA:
                new_fna_idx = s_i
            elif shf.name == SHIFT_UTD:
                new_utd_idx = s_i
            elif shf.name == SHIFT_MCY:
                new_mcy_idx = s_i

        heavy_shifts = []
        if new_eus_idx is not None:
            heavy_shifts.append(new_eus_idx)
        if new_fna_idx is not None:
            heavy_shifts.append(new_fna_idx)
        if new_utd_idx is not None:
            heavy_shifts.append(new_utd_idx)
        if new_mcy_idx is not None:
            heavy_shifts.append(new_mcy_idx)

        if heavy_shifts:
            for e, stf in enumerate(staff_list):
                for d in range(len(day_list) - 1):
                    day_d_sum = model.NewIntVar(0, len(heavy_shifts), f"day{d}_heavy_e{e}")
                    day_dplus1_sum = model.NewIntVar(0, len(heavy_shifts), f"day{d+1}_heavy_e{e}")

                    model.Add(day_d_sum == sum(assign[(d, hs, e)] for hs in heavy_shifts))
                    model.Add(day_dplus1_sum == sum(assign[(d+1, hs, e)] for hs in heavy_shifts))

                    model.Add(day_d_sum + day_dplus1_sum <= 1)

        # (N.6) KL’s preferences
        SHIFT_EBUS = "Prep EBUS"
        SHIFT_CLERICAL = "Prep Clerical"
        SHIFT_GYN = "Prep GYN"

        KL_MIN_EBUS = 2
        KL_MIN_CLERICAL = 1
        KL_MIN_GYN = 1

        KL_PENALTY_EBUS = 5
        KL_PENALTY_CLERICAL = 5
        KL_PENALTY_GYN = 5

        idx_ebus = None
        idx_cler = None
        idx_gyn = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_EBUS:
                idx_ebus = s_i
            elif shf.name == SHIFT_CLERICAL:
                idx_cler = s_i
            elif shf.name == SHIFT_GYN:
                idx_gyn = s_i

        kl_index = None
        for e_i, stf in enumerate(staff_list):
            if stf.initials == "KL":
                kl_index = e_i
                break

        kl_shortfall_vars = []
        if kl_index is not None:
            for w in unique_weeks:
                ebus_bools = []
                cler_bools = []
                gyn_bools = []
                for d, day in enumerate(day_list):
                    if week_map[d] == w:
                        if idx_ebus is not None:
                            ebus_bools.append(assign[(d, idx_ebus, kl_index)])
                        if idx_cler is not None:
                            cler_bools.append(assign[(d, idx_cler, kl_index)])
                        if idx_gyn is not None:
                            gyn_bools.append(assign[(d, idx_gyn, kl_index)])

                # EBUS
                if ebus_bools:
                    sum_ebus = model.NewIntVar(0, len(ebus_bools), f"sum_ebus_w{w}")
                    model.Add(sum_ebus == sum(ebus_bools))
                    short_ebus = model.NewIntVar(0, KL_MIN_EBUS, f"short_ebus_w{w}")
                    model.Add(short_ebus >= KL_MIN_EBUS - sum_ebus)
                    model.Add(short_ebus >= 0)
                    kl_shortfall_vars.append((short_ebus, KL_PENALTY_EBUS))

                # Clerical
                if cler_bools:
                    sum_cler = model.NewIntVar(0, len(cler_bools), f"sum_cler_w{w}")
                    model.Add(sum_cler == sum(cler_bools))
                    short_cler = model.NewIntVar(0, KL_MIN_CLERICAL, f"short_cler_w{w}")
                    model.Add(short_cler >= KL_MIN_CLERICAL - sum_cler)
                    model.Add(short_cler >= 0)
                    kl_shortfall_vars.append((short_cler, KL_PENALTY_CLERICAL))

                # GYN
                if gyn_bools:
                    sum_gyn = model.NewIntVar(0, len(gyn_bools), f"sum_gyn_w{w}")
                    model.Add(sum_gyn == sum(gyn_bools))
                    short_gyn = model.NewIntVar(0, KL_MIN_GYN, f"short_gyn_w{w}")
                    model.Add(short_gyn >= KL_MIN_GYN - sum_gyn)
                    model.Add(short_gyn >= 0)
                    kl_shortfall_vars.append((short_gyn, KL_PENALTY_GYN))

        kl_penalty_exprs = []
        for (sf_var, pen_val) in kl_shortfall_vars:
            kl_penalty_exprs.append(sf_var * pen_val)

        # ~~~~~ EFFORT MAP logic ~~~~~
        def get_day_label(day_obj):
            # If Friday => EBUS vs Regular
            if day_obj.strftime("%A") == "Friday":
                return "EBUS Friday" if is_ebus_friday else "Regular Friday"
            return day_obj.strftime("%A")

        def get_effort_value(shift_name, day_label):
            return EFFORT_MAP.get(day_label, {}).get(shift_name, DEFAULT_EFFORT)

        # Summation of day-shift efforts for staff w/ >3 trained
        staff_effort_vars = []
        max_effort_cap = 99999
        for e, stf in enumerate(staff_list):
            if not is_specialized_staff(stf):
                staff_eff_var = model.NewIntVar(0, max_effort_cap, f"effort_e{e}")
                staff_effort_vars.append((e, staff_eff_var))

        for (e, eff_var) in staff_effort_vars:
            partial_sum = []
            for d, day_obj in enumerate(day_list):
                day_lbl = get_day_label(day_obj)
                for s, shift_obj in enumerate(shifts):
                    effort_val = get_effort_value(shift_obj.name, day_lbl)
                    partial_sum.append(effort_val * assign[(d, s, e)])
            model.Add(eff_var == sum(partial_sum))

        if staff_effort_vars:
            max_effort = model.NewIntVar(0, max_effort_cap, "max_effort")
            min_effort = model.NewIntVar(0, max_effort_cap, "min_effort")
            for (e, eff_var) in staff_effort_vars:
                model.Add(eff_var <= max_effort)
                model.Add(eff_var >= min_effort)
            diff_effort = model.NewIntVar(0, max_effort_cap, "diff_effort")
            model.Add(diff_effort == max_effort - min_effort)
        else:
            diff_effort = model.NewIntVar(0, 0, "dummy_diff_effort")
            model.Add(diff_effort == 0)

        # >>> NEW: Soft penalty for using 'Cyto IMG' (prefer 'Cyto Nons 2' over 'Cyto IMG')
        SHIFT_IMG = "Cyto IMG"
        SHIFT_IMG_PENALTY = 2
        shift_img_index = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_IMG:
                shift_img_index = s_i
                break

        img_usage_var = model.NewIntVar(0, len(day_list)*len(staff_list), "img_usage")
        if shift_img_index is not None:
            model.Add(img_usage_var == sum(assign[(d, shift_img_index, e)]
                                           for d in range(len(day_list))
                                           for e in range(len(staff_list))))
        else:
            model.Add(img_usage_var == 0)

        # (N.7) TS/TG must fill "Prep Nons 1" each day it runs
        SHIFT_PREP_NONS1 = "Prep NONS 1"
        ts_index = None
        tg_index = None
        for e_i, stf in enumerate(staff_list):
            if stf.initials == "TS":
                ts_index = e_i
            elif stf.initials == "TG":
                tg_index = e_i

        prep_nons1_index = None
        for s_i, shf in enumerate(shifts):
            if shf.name == SHIFT_PREP_NONS1:
                prep_nons1_index = s_i
                break

        if prep_nons1_index is not None and ts_index is not None and tg_index is not None:
            for d, day in enumerate(day_list):
                day_str = day.strftime("%Y-%m-%d")
                # Skip if it's a holiday or shift doesn't run
                if self.availability_manager.is_holiday(day_str):
                    continue
                day_name = day.strftime("%A")
                if day_name not in shifts[prep_nons1_index].days_of_week:
                    continue
                # If forced => skip
                if (day_str, SHIFT_PREP_NONS1) in preassigned:
                    continue

                # Exactly 1 of TS or TG => 1
                model.Add(
                    assign[(d, prep_nons1_index, ts_index)]
                    + assign[(d, prep_nons1_index, tg_index)]
                    == 1
                )
                # No one else is allowed
                for e_other in range(len(staff_list)):
                    if e_other not in [ts_index, tg_index]:
                        model.Add(assign[(d, prep_nons1_index, e_other)] == 0)

        # WeightedObjective
        WeightedObjective = model.NewIntVar(0, 999999, "WeightedObjective")

        repeat_sum = sum(repeat_penalty_vars) if repeat_penalty_vars else 0
        fna_eus_sum = sum(fna_eus_penalty_vars) if fna_eus_penalty_vars else 0
        SHIFT_REPEATS_PENALTY = 10
        FNA_EUS_PENALTY = 8
        UNFILLED_OPT_PENALTY = 5

        model.Add(
            WeightedObjective
            == diff
            + diff_effort
            + 10 * total_casual_usage
            + SHIFT_REPEATS_PENALTY * repeat_sum
            + UNFILLED_OPT_PENALTY * sum(unfilled_opt_vars)
            + FNA_EUS_PENALTY * fna_eus_sum
            + sum(kl_penalty_exprs)
            + SHIFT_IMG_PENALTY * img_usage_var
        )
        model.Minimize(WeightedObjective)

        # Enforce forced picks
        for (forced_day_str, forced_shift_name), forced_init in preassigned.items():
            if forced_day_str not in day_to_idx:
                print(f"WARNING: forced day {forced_day_str} not in scheduling range!")
                continue
            if forced_shift_name not in shiftname_to_idx:
                print(f"WARNING: forced shift {forced_shift_name} unknown!")
                continue
            if forced_init not in staff_init_to_idx:
                print(f"WARNING: forced staff {forced_init} unknown!")
                continue

            d_i = day_to_idx[forced_day_str]
            s_i = shiftname_to_idx[forced_shift_name]
            e_i = staff_init_to_idx[forced_init]
            model.Add(assign[(d_i, s_i, e_i)] == 1)
            for other_e in range(len(staff_list)):
                if other_e != e_i:
                    model.Add(assign[(d_i, s_i, other_e)] == 0)

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.log_search_progress = True
        print("\n=== Debug: Solving CP model... ===")
        status = solver.Solve(model)

        final_schedule = {}
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print("\n=== Debug: Schedule Assignments ===")
            for d, day in enumerate(day_list):
                day_str = day.strftime("%Y-%m-%d")
                final_schedule[day_str] = []
                for s, shift_obj in enumerate(shifts):
                    # skip if not day_of_week and not forced
                    if (day_str, shift_obj.name) not in preassigned and day.strftime(
                        "%A"
                    ) not in shift_obj.days_of_week:
                        continue

                    assigned_emp = "Unassigned"
                    for e, stf in enumerate(staff_list):
                        if solver.Value(assign[(d, s, e)]) == 1:
                            assigned_emp = stf.initials
                            print(f"DEBUG: {day_str}, Shift '{shift_obj.name}' => {assigned_emp}")
                            break

                    final_schedule[day_str].append({
                        'shift': shift_obj.name,
                        'assigned_to': assigned_emp,
                        'role': shift_obj.role_required,
                        'is_flexible': getattr(shift_obj, 'is_flexible', False),
                        'can_remain_open': getattr(shift_obj, 'can_remain_open', False),
                    })

            print("\n=== Debug: Over-Shift (no penalty) ===")
            for o_var in over_shift_vars:
                ov = solver.Value(o_var)
                if ov > 0:
                    print(f"Over shift limit by {ov} for some staff/week.")
        else:
            print("No feasible solution found.")

        return final_schedule

    def _date_range(self, start_str, end_str):
        """
        Returns a list of date objects (Mon-Fri only) from start to end inclusive.
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
