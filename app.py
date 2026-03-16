import os, json, io, re
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Expense
from datetime import datetime, date, timedelta
from collections import defaultdict
import calendar

app = Flask(__name__)
app.config['SECRET_KEY']       = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

ADMIN_EMAIL    = os.environ.get('ADMIN_EMAIL',    'admin@expensetracker.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ── AI ENGINE (smart rule-based, always works, zero API dependency) ───────────
CATEGORIES = ['Food','Transport','Shopping','Bills','Entertainment','Health','Education','Other']

def get_user_stats(user_id):
    expenses = Expense.query.filter_by(user_id=user_id).all()
    if not expenses:
        return None
    today = date.today()
    this_month  = [e for e in expenses if e.date.month==today.month and e.date.year==today.year]
    last_month_date = (today.replace(day=1) - timedelta(days=1))
    last_month  = [e for e in expenses if e.date.month==last_month_date.month and e.date.year==last_month_date.year]

    cat_this  = defaultdict(float)
    cat_last  = defaultdict(float)
    for e in this_month:  cat_this[e.category]  += float(e.amount)
    for e in last_month:  cat_last[e.category]  += float(e.amount)

    total_this = sum(cat_this.values())
    total_last = sum(cat_last.values())

    days_this_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed    = today.day
    daily_avg       = total_this / days_elapsed if days_elapsed else 0
    projected       = daily_avg * days_this_month

    # Health Score calculation
    score = 100
    if total_last > 0 and total_this > total_last:
        pct = (total_this - total_last) / total_last * 100
        score -= min(int(pct * 0.5), 30)
    essential = cat_this.get('Bills',0) + cat_this.get('Health',0) + cat_this.get('Food',0)
    discretionary = cat_this.get('Shopping',0) + cat_this.get('Entertainment',0)
    if total_this > 0 and discretionary/total_this > 0.4:
        score -= 15
    if len(set(e.date for e in this_month)) >= 10:
        score += 5
    score = max(20, min(100, score))

    # Streak
    dates = sorted(set(e.date for e in expenses), reverse=True)
    streak = 0
    check_date = today
    for d in dates:
        if d == check_date or d == check_date - timedelta(days=1):
            streak += 1
            check_date = d
        else:
            break

    # Personality
    if total_this == 0:
        personality = ("🌱 Fresh Starter", "Just beginning your financial journey")
    elif cat_this.get('Food',0)/max(total_this,1) > 0.4:
        personality = ("🍽️ Foodie Spender", "Food is your happy place — and your wallet knows it")
    elif cat_this.get('Shopping',0)/max(total_this,1) > 0.35:
        personality = ("🛍️ Retail Enthusiast", "You shop with purpose (and sometimes without)")
    elif cat_this.get('Entertainment',0)/max(total_this,1) > 0.3:
        personality = ("🎭 Experience Collector", "You invest in memories over things")
    elif discretionary/max(total_this,1) < 0.2:
        personality = ("🎯 Budget Ninja", "Disciplined, focused, financially sharp")
    elif total_this < total_last * 0.9 and total_last > 0:
        personality = ("📉 Smart Saver", "Consistently spending less — impressive discipline")
    else:
        personality = ("⚖️ Balanced Spender", "You keep spending reasonably balanced across categories")

    top_cat = max(cat_this, key=cat_this.get) if cat_this else None

    return {
        'cat_this': dict(cat_this), 'cat_last': dict(cat_last),
        'total_this': total_this,   'total_last': total_last,
        'daily_avg': daily_avg,     'projected': projected,
        'health_score': score,      'streak': streak,
        'personality': personality, 'top_cat': top_cat,
        'days_elapsed': days_elapsed, 'days_this_month': days_this_month,
        'this_month_expenses': this_month
    }

def ai_insights(stats):
    if not stats or stats['total_this'] == 0:
        return [
            {"icon":"💡","title":"Get Started","body":"Add your first expense to unlock AI insights tailored to your spending.","color":"blue"},
            {"icon":"📊","title":"Track Daily","body":"Logging expenses daily gives the AI enough data to spot patterns and opportunities.","color":"purple"},
            {"icon":"🎯","title":"Set a Goal","body":"Try to track at least 5 categories this month for a complete financial picture.","color":"green"},
            {"icon":"🔥","title":"Build a Streak","body":"Consistent tracking unlocks your Streak badge and more accurate predictions.","color":"orange"},
        ]
    cards = []
    ct, cl = stats['cat_this'], stats['cat_last']
    tt, tl = stats['total_this'], stats['total_last']
    top    = stats['top_cat']

    # Card 1: top category
    if top:
        pct = ct[top]/tt*100
        cards.append({"icon":"🏆","title":f"{top} Leads","body":f"₹{ct[top]:,.0f} spent on {top} this month — {pct:.0f}% of your total spending.","color":"blue"})

    # Card 2: month comparison
    if tl > 0:
        diff = (tt - tl)/tl*100
        arrow = "📈 up" if diff>0 else "📉 down"
        cards.append({"icon":"📅","title":"Month Comparison","body":f"Spending is {arrow} {abs(diff):.0f}% vs last month (₹{tt:,.0f} vs ₹{tl:,.0f}).","color":"purple" if diff>0 else "green"})

    # Card 3: biggest jump
    jumps = {c: (ct.get(c,0)-cl.get(c,0))/cl[c]*100 for c in cl if cl[c]>0 and ct.get(c,0)>0}
    if jumps:
        top_jump = max(jumps, key=jumps.get)
        pj = jumps[top_jump]
        if abs(pj) > 10:
            icon = "⚠️" if pj>0 else "✅"
            word = "jumped" if pj>0 else "dropped"
            cards.append({"icon":icon,"title":f"{top_jump} {word.title()}","body":f"{top_jump} spending {word} {abs(pj):.0f}% this month. {'Consider reviewing this category.' if pj>0 else 'Great discipline here!'}","color":"orange" if pj>0 else "green"})

    # Card 4: savings opportunity
    for cat in ['Shopping','Entertainment','Food']:
        if ct.get(cat,0) > 500:
            save = ct[cat]*0.15
            annual = save*12
            cards.append({"icon":"💡","title":f"Save on {cat}","body":f"Cutting {cat} by 15% saves ₹{save:,.0f}/month — that's ₹{annual:,.0f}/year!","color":"teal"})
            break
    else:
        cards.append({"icon":"⭐","title":"Daily Rate","body":f"You're spending ₹{stats['daily_avg']:,.0f}/day. Projected month total: ₹{stats['projected']:,.0f}.","color":"blue"})

    return cards[:4]

def ai_budget(stats):
    if not stats or stats['total_this'] == 0:
        return [
            {"icon":"📋","title":"No Data Yet","body":"Add expenses to receive personalized budget recommendations.","color":"blue"},
            {"icon":"💰","title":"50/30/20 Rule","body":"Try allocating 50% to needs, 30% to wants, and 20% to savings.","color":"green"},
            {"icon":"🎯","title":"Set Category Caps","body":"Start by capping your top 2 spending categories at last month's amount.","color":"purple"},
            {"icon":"📱","title":"Daily Check-in","body":"Reviewing your expenses daily takes 30 seconds and prevents overspending.","color":"orange"},
        ]
    cards = []
    ct, cl = stats['cat_this'], stats['cat_last']
    tt = stats['total_this']

    for cat in ['Food','Shopping','Entertainment','Transport','Bills','Health']:
        spent = ct.get(cat, 0)
        prev  = cl.get(cat, 0)
        if spent == 0: continue
        pct = spent/tt*100
        if prev > 0 and spent > prev*1.2:
            diff = spent - prev
            cap  = prev*1.1
            cards.append({"icon":"🔴","title":f"Cap {cat}","body":f"₹{spent:,.0f} this month vs ₹{prev:,.0f} last. Cap at ₹{cap:,.0f} to save ₹{diff:,.0f}.","color":"red"})
        elif prev > 0 and spent < prev*0.9:
            cards.append({"icon":"✅","title":f"{cat} on Track","body":f"₹{spent:,.0f} vs ₹{prev:,.0f} last month — down {(prev-spent)/prev*100:.0f}%. Keep it up!","color":"green"})
        elif pct > 35:
            cards.append({"icon":"⚠️","title":f"{cat} Dominates","body":f"{cat} is {pct:.0f}% of spending. Consider redistributing to savings or other goals.","color":"orange"})
        if len(cards) == 4: break

    while len(cards) < 4:
        cards.append({"icon":"💡","title":"Savings Tip","body":f"Your current spending pace projects ₹{stats['projected']:,.0f} this month. Review your top category.","color":"blue"})

    return cards[:4]

def ai_chat_response(question, user_id):
    q = question.lower().strip()
    stats = get_user_stats(user_id)
    if not stats:
        return "Add some expenses first, then I can answer questions about your spending! 💡"
    ct, cl = stats['cat_this'], stats['cat_last']
    tt, tl = stats['total_this'], stats['total_last']

    # Category questions
    for cat in CATEGORIES:
        if cat.lower() in q:
            spent = ct.get(cat, 0)
            if spent == 0:
                return f"You haven't logged any {cat} expenses this month yet."
            prev = cl.get(cat, 0)
            msg = f"You've spent **₹{spent:,.0f}** on {cat} this month"
            if prev > 0:
                diff = (spent-prev)/prev*100
                msg += f", which is {'up' if diff>0 else 'down'} {abs(diff):.0f}% vs last month's ₹{prev:,.0f}"
            return msg + "."

    # Total / overall
    if any(w in q for w in ['total','overall','much','spend','spent','this month']):
        return f"This month you've spent **₹{tt:,.0f}** across {len(ct)} categories. Daily average: ₹{stats['daily_avg']:,.0f}. Projected end-of-month: ₹{stats['projected']:,.0f}."

    # Compare
    if any(w in q for w in ['compare','last month','vs','versus','difference']):
        if tl == 0:
            return "No last month data yet to compare."
        diff = tt - tl
        pct  = abs(diff)/tl*100
        word = "more" if diff>0 else "less"
        return f"You've spent **₹{abs(diff):,.0f} {word}** than last month ({pct:.0f}% {'increase' if diff>0 else 'decrease'}). This month: ₹{tt:,.0f}, last month: ₹{tl:,.0f}."

    # Top / biggest
    if any(w in q for w in ['top','biggest','most','largest','highest']):
        if not ct:
            return "No expenses logged yet this month."
        top = max(ct, key=ct.get)
        return f"Your biggest spending category is **{top}** at ₹{ct[top]:,.0f} ({ct[top]/tt*100:.0f}% of total)."

    # Save / savings / reduce
    if any(w in q for w in ['save','saving','reduce','cut','less']):
        if not ct:
            return "Add expenses first so I can suggest where to save."
        discretionary = {c: ct[c] for c in ['Shopping','Entertainment','Food'] if c in ct}
        if discretionary:
            top_disc = max(discretionary, key=discretionary.get)
            save_15  = discretionary[top_disc]*0.15
            return f"Cutting **{top_disc}** by 15% saves ₹{save_15:,.0f}/month — ₹{save_15*12:,.0f}/year. Small changes compound fast! 💰"
        return "Your spending looks pretty lean already! Keep it up. 🎯"

    # Health score
    if any(w in q for w in ['health','score','rating']):
        s = stats['health_score']
        grade = "Excellent 🌟" if s>=85 else "Good 👍" if s>=70 else "Fair ⚠️" if s>=50 else "Needs Work 📉"
        return f"Your Financial Health Score is **{s}/100** — {grade}. It's based on spending trends, category balance, and tracking consistency."

    # Streak
    if 'streak' in q:
        return f"Your current tracking streak is **{stats['streak']} day(s)**. Stay consistent to build better financial habits! 🔥"

    # Personality
    if any(w in q for w in ['personality','type','kind of']):
        p = stats['personality']
        return f"Your spending personality: **{p[0]}** — {p[1]}."

    # Prediction
    if any(w in q for w in ['predict','projection','end of month','forecast']):
        return f"Based on your ₹{stats['daily_avg']:,.0f}/day average over {stats['days_elapsed']} days, you're projected to spend **₹{stats['projected']:,.0f}** this month."

    # Fallback with context
    tips = [
        f"You've spent ₹{tt:,.0f} this month. Ask me: 'How much on food?' or 'Compare last month'.",
        f"Your top category is {stats['top_cat'] or 'unknown'}. Want tips on reducing it? Ask me!",
        f"Try asking: 'What's my health score?', 'Where can I save?', or 'What's my streak?'",
    ]
    import random
    return random.choice(tips)

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user     = User.query.get(session['user_id'])
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc(), Expense.id.desc()).all()
    stats    = get_user_stats(session['user_id'])
    return render_template('index.html', user=user, expenses=expenses, stats=stats, categories=CATEGORIES)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user     = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Welcome back! 👋', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email    = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            user = User(username=username, email=email, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            session['user_id']  = user.id
            session['username'] = user.username
            flash('Account created! 🎉', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── EXPENSE CRUD ──────────────────────────────────────────────────────────────
@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        amount      = float(request.form.get('amount', 0))
        description = request.form.get('description','').strip()
        category    = request.form.get('category','Other')
        date_str    = request.form.get('date', str(date.today()))
        exp_date    = datetime.strptime(date_str, '%Y-%m-%d').date()
        if amount <= 0:
            flash('Amount must be positive.', 'error')
        else:
            expense = Expense(user_id=session['user_id'], amount=amount,
                              description=description, category=category, date=exp_date)
            db.session.add(expense)
            db.session.commit()
            flash('Expense added! ✅', 'success')
    except ValueError:
        flash('Invalid amount or date.', 'error')
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.filter_by(id=id, user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        expense.amount      = float(request.form.get('amount', expense.amount))
        expense.description = request.form.get('description', expense.description).strip()
        expense.category    = request.form.get('category', expense.category)
        date_str = request.form.get('date', str(expense.date))
        expense.date        = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.session.commit()
        flash('Expense updated! ✅', 'success')
        return redirect(url_for('index'))
    return render_template('edit_expense.html', expense=expense, categories=CATEGORIES)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.filter_by(id=id, user_id=session['user_id']).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'success')
    return redirect(url_for('index'))

# ── ANALYTICS ─────────────────────────────────────────────────────────────────
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('analytics.html', user=user)

@app.route('/api/analytics-data')
def api_analytics_data():
    if 'user_id' not in session:
        return jsonify({'error':'unauthorized'}), 401
    expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    today    = date.today()

    # Last 6 months trend
    trend_labels, trend_data = [], []
    for i in range(5, -1, -1):
        d   = (today.replace(day=1) - timedelta(days=i*28)).replace(day=1)
        tot = sum(float(e.amount) for e in expenses if e.date.month==d.month and e.date.year==d.year)
        trend_labels.append(d.strftime('%b'))
        trend_data.append(round(tot, 2))

    # Category donut
    cat_totals = defaultdict(float)
    for e in expenses:
        if e.date.month==today.month and e.date.year==today.year:
            cat_totals[e.category] += float(e.amount)
    donut_labels = list(cat_totals.keys())
    donut_data   = [round(v,2) for v in cat_totals.values()]

    # Month comparison bar
    this_cats = defaultdict(float)
    last_date = (today.replace(day=1) - timedelta(days=1))
    last_cats = defaultdict(float)
    for e in expenses:
        if e.date.month==today.month and e.date.year==today.year:
            this_cats[e.category] += float(e.amount)
        elif e.date.month==last_date.month and e.date.year==last_date.year:
            last_cats[e.category] += float(e.amount)
    all_cats  = sorted(set(list(this_cats.keys())+list(last_cats.keys())))

    return jsonify({
        'trend':  {'labels':trend_labels, 'data':trend_data},
        'donut':  {'labels':donut_labels, 'data':donut_data},
        'bar':    {'categories':all_cats,
                   'this_month':[round(this_cats.get(c,0),2) for c in all_cats],
                   'last_month':[round(last_cats.get(c,0),2) for c in all_cats]}
    })

# ── AI API ENDPOINTS ──────────────────────────────────────────────────────────
@app.route('/api/ai-insights')
def api_ai_insights():
    if 'user_id' not in session:
        return jsonify({'error':'unauthorized'}), 401
    stats = get_user_stats(session['user_id'])
    return jsonify({'insights': ai_insights(stats)})

@app.route('/api/ai-budget')
def api_ai_budget():
    if 'user_id' not in session:
        return jsonify({'error':'unauthorized'}), 401
    stats = get_user_stats(session['user_id'])
    return jsonify({'recommendations': ai_budget(stats)})

@app.route('/api/ai-chat', methods=['POST'])
def api_ai_chat():
    if 'user_id' not in session:
        return jsonify({'error':'unauthorized'}), 401
    question = request.json.get('message','').strip()
    if not question:
        return jsonify({'response':'Please type a question.'})
    response = ai_chat_response(question, session['user_id'])
    return jsonify({'response': response})

# ── ADMIN ─────────────────────────────────────────────────────────────────────
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.email != ADMIN_EMAIL:
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    users    = User.query.all()
    expenses = Expense.query.all()
    cat_data = defaultdict(float)
    for e in expenses: cat_data[e.category] += float(e.amount)
    return render_template('admin.html', user=user, users=users, expenses=expenses,
                           cat_labels=list(cat_data.keys()), cat_values=[round(v,2) for v in cat_data.values()])

# ── SETTINGS ──────────────────────────────────────────────────────────────────
@app.route('/settings', methods=['GET','POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'profile':
            new_username = request.form.get('username','').strip()
            if new_username:
                user.username = new_username
                session['username'] = new_username
                db.session.commit()
                flash('Profile updated! ✅', 'success')
        elif action == 'password':
            current = request.form.get('current_password','')
            new_pw  = request.form.get('new_password','')
            if check_password_hash(user.password, current):
                if len(new_pw) >= 6:
                    user.password = generate_password_hash(new_pw)
                    db.session.commit()
                    flash('Password updated! ✅', 'success')
                else:
                    flash('New password must be 6+ characters.', 'error')
            else:
                flash('Current password incorrect.', 'error')
    return render_template('settings.html', user=user)

# ── PDF EXPORT ────────────────────────────────────────────────────────────────
@app.route('/pdf')
def export_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user     = User.query.get(session['user_id'])
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).all()
    today    = date.today()
    this_m   = [e for e in expenses if e.date.month==today.month and e.date.year==today.year]
    total    = sum(float(e.amount) for e in this_m)
    cat_data = defaultdict(float)
    for e in this_m: cat_data[e.category] += float(e.amount)

    lines  = [f"EXPENSE REPORT — {today.strftime('%B %Y')}", f"Generated: {today}", f"User: {user.username}", "="*50]
    lines += [f"Total This Month: Rs.{total:,.2f}", f"Total Transactions: {len(this_m)}", "="*50]
    lines += ["\nCATEGORY BREAKDOWN:"]
    for cat,amt in sorted(cat_data.items(), key=lambda x:-x[1]):
        lines.append(f"  {cat:15s}  Rs.{amt:>10,.2f}  ({amt/total*100:.1f}%)" if total>0 else f"  {cat}")
    lines += ["\n"+"-"*50, "TRANSACTIONS:"]
    for e in this_m:
        lines.append(f"  {str(e.date):<12}  {e.category:<15}  Rs.{float(e.amount):>9,.2f}  {e.description[:30]}")

    content = "\n".join(lines)
    response = make_response(content)
    response.headers['Content-Type']        = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=expense_report_{today.strftime("%Y_%m")}.txt'
    return response

# ── STARTUP ───────────────────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email=ADMIN_EMAIL).first():
            admin = User(username='Admin', email=ADMIN_EMAIL,
                        password=generate_password_hash(ADMIN_PASSWORD))
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created")
    print("✅ Database ready")

init_db()

if __name__ == '__main__':
    app.run(debug=True)
