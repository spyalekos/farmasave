from datetime import datetime, timedelta
from . import database

def get_depletion_info():
    meds = database.get_all_medications()
    depletion_list = []
    now = datetime.now().date()
    for med in meds:
        # med: (id, name, typ, ppb, boxes, pieces, dosage, inv_date)
        med_id, name, typ, ppb, boxes, pieces, dosage, inv_date_str = med
        dosage = dosage if dosage is not None else 0
        
        # Calculate initial total
        initial_total = pieces + (boxes * ppb)
        
        # Calculate consumption since inventory date
        if inv_date_str:
            inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
            days_passed = (now - inv_date).days
            consumed = days_passed * dosage
        else:
            consumed = 0
            
        current_total = max(0, initial_total - consumed)
        
        if dosage > 0 and current_total > 0:
            days_left = current_total / dosage
            depletion_date = datetime.now() + timedelta(days=days_left)
            depletion_list.append((name, depletion_date.date(), days_left, current_total))
        elif dosage > 0 and current_total <= 0:
            # Already ran out
            depletion_list.append((name, now, 0, 0))
            
    if depletion_list:
        depletion_list.sort(key=lambda x: x[1])
        earliest = depletion_list[0]
        return earliest, depletion_list
    return None, []

def generate_schedule(days_ahead=30):
    meds = database.get_all_medications()
    schedule = []
    start_date = datetime.now().date()
    
    # Pre-calculate current stock for each med
    med_status = []
    for med in meds:
        med_id, name, typ, ppb, boxes, pieces, dosage, inv_date_str = med
        dosage = dosage if dosage is not None else 0
        initial_total = pieces + (boxes * ppb)
        if inv_date_str:
            inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
            days_passed = (start_date - inv_date).days
            consumed = days_passed * dosage
        else:
            consumed = 0
        current_total = max(0, initial_total - consumed)
        med_status.append({'name': name, 'dosage': dosage, 'stock': current_total})

    for i in range(days_ahead):
        date = start_date + timedelta(days=i)
        day_meds = []
        for status in med_status:
            if status['dosage'] > 0 and status['stock'] > 0:
                day_meds.append(status['name'])
                status['stock'] -= status['dosage']
        if day_meds:
            schedule.append((date, day_meds))
    return schedule
