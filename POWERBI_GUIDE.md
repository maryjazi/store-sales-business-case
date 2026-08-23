# راهنمای ساخت داشبورد Power BI (مرحله‌به‌مرحله)

فایل‌های داده توی `dashboard/data/` آماده‌ست:

| فایل | نوع | توضیح |
|---|---|---|
| `fact_sales_actual.parquet` | Fact | فروش واقعی، سطح date × store × family (۳M ردیف) |
| `fact_sales_forecast.parquet` | Fact | پیش‌بینی مدل برای ۱۶ روز آینده (۲۸٬۵۱۲ ردیف) |
| `dim_store.csv` | Dimension | ۵۴ فروشگاه: شهر، استان، نوع، cluster |
| `dim_date.csv` | Dimension | تقویم کامل (شامل بازه پیش‌بینی) |
| `dim_family.csv` | Dimension | ۳۳ دسته کالا + گروه‌بندی کسب‌وکاری |

---

## قدم ۱: Import داده‌ها

1. Power BI Desktop رو باز کن → **Get Data**
2. برای دو فایل parquet: **Get Data → More → Parquet** → مسیر فایل رو بده
3. برای سه فایل csv: **Get Data → Text/CSV**
4. هر ۵ تا رو Load کن (نه Import ساده — دکمه **Load** بعد از پیش‌نمایش)

## قدم ۲: ساخت Star Schema (تب Model)

برو به تب **Model view** و این رابطه‌ها رو دستی بکش (drag از ستون به ستون):

- `dim_store[store_nbr]` → `fact_sales_actual[store_nbr]` (۱ به چند)
- `dim_store[store_nbr]` → `fact_sales_forecast[store_nbr]`
- `dim_family[family]` → `fact_sales_actual[family]`
- `dim_family[family]` → `fact_sales_forecast[family]`
- `dim_date[date]` → `fact_sales_actual[date]`
- `dim_date[date]` → `fact_sales_forecast[date]`

نکته: هر دو فکت (actual و forecast) به همون dim_store/dim_date/dim_family وصل می‌شن — این الگوی استاندارد "چند فکت، یک ستاره" هست.

## قدم ۳: DAX Measures

برو به تب **Report**، روی `fact_sales_actual` راست‌کلیک → **New Measure**، و این‌ها رو یکی‌یکی بساز:

```dax
Total Sales = SUM(fact_sales_actual[sales])

Total Forecast Sales = SUM(fact_sales_forecast[forecast_sales])

Avg Daily Sales = DIVIDE([Total Sales], DISTINCTCOUNT(fact_sales_actual[date]))

YoY Sales Growth % =
VAR CurrentSales = [Total Sales]
VAR PriorYearSales = CALCULATE([Total Sales], SAMEPERIODLASTYEAR(dim_date[date]))
RETURN DIVIDE(CurrentSales - PriorYearSales, PriorYearSales)

Holiday Uplift % =
VAR HolidayAvg = CALCULATE(AVERAGE(fact_sales_actual[sales]), fact_sales_actual[is_holiday] = TRUE)
VAR RegularAvg = CALCULATE(AVERAGE(fact_sales_actual[sales]), fact_sales_actual[is_holiday] = FALSE)
RETURN DIVIDE(HolidayAvg - RegularAvg, RegularAvg)

Payday Uplift % =
VAR PaydayAvg = CALCULATE(AVERAGE(fact_sales_actual[sales]), fact_sales_actual[is_payday] = TRUE)
VAR RegularAvg = CALCULATE(AVERAGE(fact_sales_actual[sales]), fact_sales_actual[is_payday] = FALSE)
RETURN DIVIDE(PaydayAvg - RegularAvg, RegularAvg)

Sales Rank by Store = RANKX(ALL(dim_store[store_nbr]), [Total Sales], , DESC)
```

## قدم ۴: ویژوال‌ها (پیشنهاد صفحه‌بندی)

**صفحه ۱ — Overview:**
- ۴ تا کارت (Card): Total Sales، Avg Daily Sales، YoY Sales Growth %، Total Forecast Sales
- نمودار خطی: `dim_date[date]` روی محور X، هم `[Total Sales]` هم `[Total Forecast Sales]` روی Y (یه خط توپر برای actual، یه خط نقطه‌چین برای forecast — این ترکیب actual+forecast رو توی یه نمودار نشون می‌ده)

**صفحه ۲ — Category & Region:**
- نمودار میله‌ای افقی: `[Total Sales]` بر اساس `dim_family[family]` (Top N = 15)
- نمودار دایره‌ای یا Treemap: `[Total Sales]` بر اساس `dim_family[family_group]`
- نقشه (Map) یا میله‌ای: `[Total Sales]` بر اساس `dim_store[city]`

**صفحه ۳ — Store Performance:**
- جدول (Table/Matrix): `dim_store[store_nbr, city, type]` + `[Total Sales]` + `[Sales Rank by Store]`
- نمودار میله‌ای: `[Total Sales]` بر اساس `dim_store[type]`

**صفحه ۴ — External Factors:**
- کارت‌ها: `[Holiday Uplift %]`, `[Payday Uplift %]`
- نمودار میله‌ای: میانگین sales بر اساس `dim_date[day_name]` (الگوی هفتگی)

## قدم ۵: Slicers (فیلترهای تعاملی)

روی هر صفحه اضافه کن:
- Slicer روی `dim_date[year]` یا بازه تاریخ (date range slicer)
- Slicer روی `dim_family[family_group]`
- Slicer روی `dim_store[type]` یا `dim_store[city]`

## قدم ۶: ذخیره

فایل رو با اسم `store_sales.pbix` توی همین پوشه (`dashboard/`) ذخیره کن، و از هر صفحه یه اسکرین‌شات بگیر و توی `dashboard/screenshots/` بذار — این‌ها برای README و پورتفولیو لازم می‌شن (فاز ۷).

---

اگه هر جا گیر کردی یا خروجی عجیب دیدی (مثلاً relationship کار نکرد یا measure خطا داد)، بگو دقیقاً چی می‌بینی تا کمک کنم رفعش کنیم.
