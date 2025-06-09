from flask import Flask, render_template, redirect, url_for, request, flash
from datetime import datetime, date
import calendar
from sqlalchemy import func
from models import db, DayRecord

# Русские названия месяцев
RU_MONTHS = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'change-this-secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Внедряем RU_MONTHS и date в контекст всех шаблонов
    @app.context_processor
    def inject_globals():
        return {
            'ru_months': RU_MONTHS,
            'date': date
        }

    @app.route('/')
    def index():
        current_year = datetime.now().year
        months = [{'number': i, 'name': RU_MONTHS[i - 1]} for i in range(1, 13)]
        return render_template('index.html', months=months, current_year=current_year)

    @app.route('/month/<int:year>/<int:month>')
    def month_view(year, month):
        days_in_month = calendar.monthrange(year, month)[1]
        days = [
            {
                'day': d,
                'weekday': date(year, month, d).strftime('%a'),
                'url': url_for('day_view', year=year, month=month, day=d)
            }
            for d in range(1, days_in_month + 1)
        ]
        return render_template(
            'month.html',
            days=days,
            month_name=RU_MONTHS[month - 1],
            year=year,
            month=month
        )

    @app.route('/month/<int:year>/<int:month>/summary')
    def month_summary(year, month):
        days_in_month = calendar.monthrange(year, month)[1]
        first_day = date(year, month, 1)
        last_day_date = date(year, month, days_in_month)

        totals = db.session.query(
            func.coalesce(func.sum(DayRecord.sugar), 0).label('sugar'),
            func.coalesce(func.sum(DayRecord.essence), 0).label('essence'),
            func.coalesce(func.sum(DayRecord.tax), 0).label('tax'),
            func.coalesce(func.sum(DayRecord.water), 0).label('water'),
            func.coalesce(func.sum(DayRecord.electricity), 0).label('electricity'),
            func.coalesce(func.sum(DayRecord.gas), 0).label('gas'),
            func.coalesce(func.sum(DayRecord.other), 0).label('other'),
            func.coalesce(func.sum(DayRecord.revenue), 0).label('revenue')
        ).filter(
            DayRecord.date.between(first_day, last_day_date)
        ).one()

        data = totals._asdict()
        data['expenses'] = sum(data[k] for k in (
            'sugar', 'essence', 'tax', 'water', 'electricity', 'gas', 'other'
        ))
        data['profit'] = data['revenue'] - data['expenses']

        day_rows = []
        for d in range(1, days_in_month + 1):
            rec = DayRecord.query.filter_by(date=date(year, month, d)).first()
            if rec:
                exp = sum(filter(None, [
                    rec.sugar, rec.essence, rec.tax, rec.water,
                    rec.electricity, rec.gas, rec.other
                ]))
                rev = rec.revenue or 0
            else:
                exp = rev = 0
            day_rows.append({
                'day': d,
                'expenses': exp,
                'revenue': rev,
                'profit': rev - exp
            })

        return render_template(
            'month_summary.html',
            month_name=RU_MONTHS[month - 1],
            year=year,
            month=month,
            data=data,
            day_rows=day_rows
        )

    @app.route('/year/<int:year>/summary')
    def year_summary(year):
        totals = db.session.query(
            func.coalesce(func.sum(DayRecord.sugar), 0).label('sugar'),
            func.coalesce(func.sum(DayRecord.essence), 0).label('essence'),
            func.coalesce(func.sum(DayRecord.tax), 0).label('tax'),
            func.coalesce(func.sum(DayRecord.water), 0).label('water'),
            func.coalesce(func.sum(DayRecord.electricity), 0).label('electricity'),
            func.coalesce(func.sum(DayRecord.gas), 0).label('gas'),
            func.coalesce(func.sum(DayRecord.other), 0).label('other'),
            func.coalesce(func.sum(DayRecord.revenue), 0).label('revenue')
        ).filter(
            func.strftime('%Y', DayRecord.date) == str(year)
        ).one()

        data = totals._asdict()
        data['expenses'] = sum(data[k] for k in (
            'sugar', 'essence', 'tax', 'water', 'electricity', 'gas', 'other'
        ))
        data['profit'] = data['revenue'] - data['expenses']

        month_rows = []
        for m in range(1, 13):
            fday = date(year, m, 1)
            lday = date(year, m, calendar.monthrange(year, m)[1])

            exp = db.session.query(
                func.coalesce(func.sum(DayRecord.sugar), 0) +
                func.coalesce(func.sum(DayRecord.essence), 0) +
                func.coalesce(func.sum(DayRecord.tax), 0) +
                func.coalesce(func.sum(DayRecord.water), 0) +
                func.coalesce(func.sum(DayRecord.electricity), 0) +
                func.coalesce(func.sum(DayRecord.gas), 0) +
                func.coalesce(func.sum(DayRecord.other), 0)
            ).filter(DayRecord.date.between(fday, lday)).scalar()

            rev = db.session.query(
                func.coalesce(func.sum(DayRecord.revenue), 0)
            ).filter(DayRecord.date.between(fday, lday)).scalar()

            month_rows.append({
                'name': RU_MONTHS[m - 1],
                'expenses': exp,
                'revenue': rev,
                'profit': rev - exp
            })

        return render_template(
            'year_summary.html',
            year=year,
            data=data,
            month_rows=month_rows
        )

    @app.route('/day/<int:year>/<int:month>/<int:day>', methods=['GET', 'POST'])
    def day_view(year, month, day):
        selected_date = date(year, month, day)
        record = DayRecord.query.filter_by(date=selected_date).first() or DayRecord(date=selected_date)

        if request.method == 'POST':
            field = request.form['field']
            value_str = request.form.get('value', '').strip()
            # если пустая строка или некорректно, ставим 0.0
            try:
                value = float(value_str) if value_str else 0.0
            except ValueError:
                value = 0.0

            real = DayRecord.query.filter_by(date=selected_date).first()
            if not real:
                real = DayRecord(date=selected_date)
                db.session.add(real)
            setattr(real, field, value)
            db.session.commit()
            flash(f'Сохранено: {field} = {value}')
            return redirect(url_for('day_view', year=year, month=month, day=day))

        cards = [
            ('sugar',       'Сахар',            record.sugar),
            ('essence',     'Эссенция',         record.essence),
            ('tax',         'Налог',            record.tax),
            ('water',       'Вода',             record.water),
            ('electricity', 'Электричество',    record.electricity),
            ('gas',         'Газ баллоны',      record.gas),
            ('other',       'Прочие расходы',   record.other),
            ('revenue',     'Выручка',          record.revenue),
        ]
        return render_template(
            'day.html',
            date=selected_date,
            cards=cards,
            record=record,
            month=month,
            year=year
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
