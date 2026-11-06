import json, re, glob, os
MOD = '../../postgresql-demodb-persistence/src/test/sql-exercises'
C = []
def fix(i, src, why, **kw): C.append(dict(op='fix', id=i, _src=src, _why=why, rerun=kw.pop('rerun', 'sql' in kw), **kw))
def add(i, src, why, **kw): C.append(dict(op='add', id=i, after=kw.pop('after', 'last'), _src=src, _why=why, rerun=True, **kw))
def rm(i, src, why): C.append(dict(op='remove', id=i, _src=src, _why=why))

# ------------------------------------------------------------------------------------------------------------ batch 1
fix('DEMODB_SEATS_A_01', 'Claude', "the SQL wrote the airplane, '7M7', in; the flight's airplane comes from the route valid at its departure",
    request=["Find the seats of the airplane that flies the flight `1` that nobody boarded: the seats with no boarding pass of that flight.",
             "Show the seat and its fare conditions, ordered by `seat_no`.",
             "The flight's airplane is the one of the route's row valid at its departure, which `timetable` gives; a `NOT EXISTS` keeps the seats with no pass."],
    sql="SELECT s.seat_no, s.fare_conditions\nFROM timetable t\n         JOIN seats s ON s.airplane_code = t.airplane_code\nWHERE t.flight_id = 1\n  AND NOT EXISTS (SELECT 1\n                  FROM boarding_passes bp\n                  WHERE bp.flight_id = t.flight_id\n                    AND bp.seat_no = s.seat_no)\nORDER BY s.seat_no")
fix('DEMODB_TIMETABLE_B_02', 'both', "the date bounds were read in the session's time zone; the UTC day, and the departure shown in UTC",
    request=["Find the rows of the route `PG0078` scheduled to depart on 2025-10-01, UTC.",
             "Show the flight, the two airports, the scheduled departure in UTC and local time, and the scheduled arrival in local time, ordered by the scheduled departure.",
             "The view has already converted the times with each airport's time zone; `AT TIME ZONE 'UTC'` shows a `timestamptz` in UTC whatever the session's zone."],
    sql="SELECT flight_id,\n       departure_airport,\n       arrival_airport,\n       scheduled_departure AT TIME ZONE 'UTC' AS scheduled_departure_utc,\n       scheduled_departure_local,\n       scheduled_arrival_local\nFROM timetable\nWHERE route_no = 'PG0078'\n  AND scheduled_departure >= TIMESTAMPTZ '2025-10-01 00:00:00+00'\n  AND scheduled_departure < TIMESTAMPTZ '2025-10-02 00:00:00+00'\nORDER BY scheduled_departure")
fix('DEMODB_TIMETABLE_A_02', 'both', "the day was the session's; Codex's local day at Sheremetyevo, over Claude's UTC day, since the question is about connections there",
    request=["For each flight scheduled to arrive at `SVO` on 2025-10-01, local time at `SVO`, find the flights departing from `SVO` between one and four hours after its scheduled arrival.",
             "Show the arriving flight, the departing flight, where it goes and the layover, ordered by the two flights; the first ten.",
             "A self join of the view on the airport and a window of time; the day is taken on `scheduled_arrival_local`, a `timestamp` in the airport's own time."],
    sql="SELECT a.flight_id                                 AS arriving,\n       d.flight_id                                 AS departing,\n       d.arrival_airport                           AS destination,\n       d.scheduled_departure - a.scheduled_arrival AS layover\nFROM timetable a\n         JOIN timetable d ON d.departure_airport = a.arrival_airport\n    AND d.scheduled_departure BETWEEN a.scheduled_arrival + INTERVAL '1 hour' AND a.scheduled_arrival + INTERVAL '4 hours'\nWHERE a.arrival_airport = 'SVO'\n  AND a.scheduled_arrival_local >= TIMESTAMP '2025-10-01 00:00:00'\n  AND a.scheduled_arrival_local < TIMESTAMP '2025-10-02 00:00:00'\nORDER BY a.flight_id, d.flight_id\nLIMIT 10")
fix('DEMODB_TIMETABLE_I_03', 'both', "the month was the session's; the late count did not ask for the status the arrived count asks for (Codex's, one definition for both)",
    request=["Group the rows by the UTC month of the scheduled arrival, and count the flights with the status `Arrived`, and, of those, the ones whose actual arrival was more than an hour after the scheduled one.",
             "Show the month, the flights that arrived and the late ones, in order.",
             "Two conditional counts with `FILTER`; `AT TIME ZONE 'UTC'` takes the month in UTC, whatever the session's zone."],
    sql="SELECT TO_CHAR(scheduled_arrival AT TIME ZONE 'UTC', 'YYYY-MM') AS month,\n       COUNT(*) FILTER (WHERE status = 'Arrived') AS arrived,\n       COUNT(*) FILTER (WHERE status = 'Arrived' AND actual_arrival > scheduled_arrival + INTERVAL '1 hour') AS late\nFROM timetable\nGROUP BY month\nORDER BY month")
fix('DEMODB_TIMETABLE_B_01', 'both', 'several flights may leave SVO at the same minute; flight_id breaks the tie',
    request=["The database's now is `bookings.now()`.",
             "Find the rows of `timetable` whose `departure_airport` is `SVO` and whose scheduled departure is within the next 24 hours of it.",
             "Show the flight, the route, the arrival airport, the local departure time and the status, ordered by the scheduled departure, then by `flight_id`."],
    sql="SELECT flight_id, route_no, arrival_airport, scheduled_departure_local, status\nFROM timetable\nWHERE departure_airport = 'SVO'\n  AND scheduled_departure >= bookings.now()\n  AND scheduled_departure < bookings.now() + INTERVAL '24 hours'\nORDER BY scheduled_departure, flight_id")
fix('DEMODB_AIRPLANES_DATA_A_02', 'both', 'the inner joins dropped an airplane with no route or no flight, though COUNT(f.flight_id) meant to show 0',
    request=["Count the flights each airplane flies, `0` for one that flies none: a flight's airplane is the one of the route's row valid at the flight's scheduled departure.",
             "Show the code, the English name and the count, the most first; airplanes with the same count are ordered by `airplane_code`.",
             "Two outer joins, the second on a range containment (`@>`), and a group."],
    sql="SELECT a.airplane_code, a.model ->> 'en' AS model, COUNT(f.flight_id) AS flights\nFROM airplanes_data a\n         LEFT JOIN routes r ON r.airplane_code = a.airplane_code\n         LEFT JOIN flights f ON f.route_no = r.route_no AND r.validity @> f.scheduled_departure\nGROUP BY a.airplane_code, a.model\nORDER BY flights DESC, a.airplane_code")
fix('DEMODB_AIRPORTS_DATA_A_01', 'both', "the groups are by city and country, but the sort only by city, so LIMIT 10 could cut between two countries' cities",
    request=["Group the airports by city and country, in English, and keep the cities with more than one.",
             "Show the city, the country, the codes joined into one string in order, and the count: the most airports first, then by city, then by country; the first ten.",
             "A group on two `jsonb` fields, `HAVING`, and `string_agg` with its own `ORDER BY`."],
    sql="SELECT city ->> 'en'                                        AS city,\n       country ->> 'en'                                     AS country,\n       STRING_AGG(airport_code, ', ' ORDER BY airport_code) AS airports,\n       COUNT(*)                                             AS count\nFROM airports_data\nGROUP BY city ->> 'en', country ->> 'en'\nHAVING COUNT(*) > 1\nORDER BY count DESC, city, country\nLIMIT 10")
fix('DEMODB_ROUTES_B_03', 'Claude', 'CARDINALITY = 7 counts the elements, which is all seven days only if none repeats; @> asks the question itself',
    request=["Find the rows whose `days_of_week` holds all seven days.",
             "Show the route number, the airports, the departure time and the validity, ordered by `route_no` and then by `validity`.",
             "`@>` asks whether one array contains another; counting the elements would hold only if no day repeats."],
    sql="SELECT route_no, departure_airport, arrival_airport, scheduled_time, validity\nFROM routes\nWHERE days_of_week @> ARRAY [1, 2, 3, 4, 5, 6, 7]\nORDER BY route_no, validity")
fix('DEMODB_ROUTES_A_02', 'both', 'the request did not say what one row is; the SQL stays',
    request=["Pair each row with a row that flies the opposite direction while the two periods of validity overlap.",
             "Show each pair of route numbers once, from the airport whose code sorts first, with the two airports, ordered by the two route numbers; the first ten.",
             "A self join on swapped airports and overlapping ranges (`&&`); the `<` on the airports keeps each pair once."])
add('DEMODB_TIMETABLE_B_03', 'Claude', 'status, a CHECK-constrained enumeration, is read by no exercise',
    title='how many flights of each status',
    request=["Count the flights of each status, and show the status and the count, ordered by the status."],
    sql="SELECT status, COUNT(*) AS flights\nFROM timetable\nGROUP BY status\nORDER BY status")
add('DEMODB_TIMETABLE_I_05', 'Claude', 'no exercise measures a delay: interval arithmetic on nullable columns, AVG over an interval, a HAVING',
    title='the ten airports with the longest average departure delay',
    request=["For the flights that have departed, average the actual minus the scheduled departure by departure airport, keeping the airports with at least 100 such flights.",
             "Show the airport, the flights and the average delay, the longest first, then by airport; the first ten.",
             "`AVG` of an `interval` is an `interval`; the `HAVING` drops the airports with too few flights to mean anything."],
    sql="SELECT departure_airport,\n       COUNT(*)                                    AS departed,\n       AVG(actual_departure - scheduled_departure) AS average_delay\nFROM timetable\nWHERE actual_departure IS NOT NULL\nGROUP BY departure_airport\nHAVING COUNT(*) >= 100\nORDER BY average_delay DESC, departure_airport\nLIMIT 10")
add('DEMODB_ROUTES_I_06', 'Claude', 'days_of_week is only tested with ANY and CARDINALITY; UNNEST turns it into rows',
    title='how many routes fly on each day of the week, now',
    request=["For the routes valid at `bookings.now()`, count the routes flown on each day of the week, `1` being Monday.",
             "Show the day and the count, in order.",
             "`UNNEST` turns each row's array into rows, one per day."],
    sql="SELECT d.day_of_week, COUNT(*) AS routes\nFROM routes r\n         CROSS JOIN UNNEST(r.days_of_week) AS d(day_of_week)\nWHERE r.validity @> bookings.now()\nGROUP BY d.day_of_week\nORDER BY d.day_of_week")
add('DEMODB_ROUTES_I_07', 'Codex', 'DEMODB_ROUTES_I_06 counts each day of an array once, which holds only if no day repeats and every day is 1 to 7; nothing enforces either',
    title='the rows whose days of the week are not a set of days',
    request=["`days_of_week` should hold days from 1 to 7, each once; nothing in the schema says so, and DEMODB_ROUTES_I_06 relies on it.",
             "Find the rows whose array is empty, holds a NULL or a value outside 1 to 7, or repeats a day, with the route, the validity and the days, ordered by route and validity; the check passes when nothing comes back."],
    sql="SELECT route_no, validity, days_of_week\nFROM routes\nWHERE CARDINALITY(days_of_week) = 0\n   OR EXISTS (SELECT 1 FROM UNNEST(days_of_week) AS d(day) WHERE day IS NULL OR day NOT BETWEEN 1 AND 7)\n   OR CARDINALITY(days_of_week) <> (SELECT COUNT(DISTINCT day) FROM UNNEST(days_of_week) AS d(day))\nORDER BY route_no, validity")
add('DEMODB_ROUTES_A_04', 'Claude', 'the DDL installs earthdistance, which no exercise uses; the airports, the airplane\'s range and the route meet here',
    title='the ten longest routes valid now, by great-circle distance',
    request=["For the routes valid at `bookings.now()`, compute the great-circle distance between the two airports, in km.",
             "Show the route, the two airports, the airplane, its range and the distance, the farthest first, then by route number; the first ten.",
             "`<@>` of `earthdistance` gives the distance between two `point`s in statute miles; 1.609344 turns it into km."],
    sql="SELECT r.route_no,\n       r.departure_airport,\n       r.arrival_airport,\n       r.airplane_code,\n       a.range,\n       ROUND(((dep.coordinates <@> arr.coordinates) * 1.609344)::numeric) AS distance_km\nFROM routes r\n         JOIN airports_data dep ON dep.airport_code = r.departure_airport\n         JOIN airports_data arr ON arr.airport_code = r.arrival_airport\n         JOIN airplanes_data a ON a.airplane_code = r.airplane_code\nWHERE r.validity @> bookings.now()\nORDER BY distance_km DESC, r.route_no\nLIMIT 10")
add('DEMODB_SEATS_I_04', 'Codex', 'the seat exercises split seat_no into a row number and a letter, which the DDL does not promise',
    title='the seat numbers which are not a row and a letter',
    request=["The seat exercises read `seat_no` as a row number followed by one letter; the schema allows any text.",
             "Find the seats whose number is not a positive row number followed by one capital letter, ordered by airplane and seat; the check passes when nothing comes back."],
    sql="SELECT airplane_code, seat_no\nFROM seats\nWHERE seat_no !~ '^[1-9][0-9]*[A-Z]$'\nORDER BY airplane_code, seat_no")
add('DEMODB_AIRPORTS_DATA_I_04', 'Codex', "the English names are grouped and filtered everywhere, while NOT NULL applies only to the json documents",
    title='the airports missing an English name, city or country',
    request=["The exercises read the English (`en`) name, city and country of each airport; the schema makes only the `jsonb` documents NOT NULL.",
             "Find the airports whose English name, city or country is missing, not a string, or blank, with the three values, ordered by code; the check passes when nothing comes back."],
    sql="SELECT airport_code,\n       airport_name ->> 'en' AS airport_name,\n       city ->> 'en'         AS city,\n       country ->> 'en'      AS country\nFROM airports_data\nWHERE JSONB_TYPEOF(airport_name -> 'en') IS DISTINCT FROM 'string'\n   OR JSONB_TYPEOF(city -> 'en') IS DISTINCT FROM 'string'\n   OR JSONB_TYPEOF(country -> 'en') IS DISTINCT FROM 'string'\n   OR BTRIM(airport_name ->> 'en') = ''\n   OR BTRIM(city ->> 'en') = ''\n   OR BTRIM(country ->> 'en') = ''\nORDER BY airport_code")
rm('DEMODB_AIRPLANES_I_02', 'both', "the view is model ->> lang() over the same table, so the comparison is empty by construction")
rm('DEMODB_AIRPORTS_DATA_B_03', 'Claude', 'the first letters of an IATA code mean nothing; LIKE is taught by DEMODB_AIRPLANES_B_02')

# ------------------------------------------------------------------------------------------------------------ batch 2
UTC = lambda d: f"TIMESTAMPTZ '{d} 00:00:00+00'"
fix('DEMODB_FLIGHTS_A_03', 'both', 'it counted every boarding pass, the checked-in but not boarded too; ranked by the rounded share; a flight with no pass was dropped',
    request=["For the flights scheduled on 2025-10-01 that arrived, count the passengers boarded, the boarding passes with a boarding number, and the seats of the flight's airplane, and keep the five with the highest share of seats boarded; flights with the same share are ordered by `flight_id`.",
             "Show the flight, the route, the airplane, the two counts and the share as a percentage to one decimal.",
             "Three joins, one of them on a range containment, the boarding passes by an outer join, a group, and a subquery for the seats; the order uses the share itself, not the rounded one."],
    sql=f"SELECT f.flight_id,\n       f.route_no,\n       r.airplane_code,\n       COUNT(bp.boarding_no)                            AS boarded,\n       s.seats,\n       ROUND(100.0 * COUNT(bp.boarding_no) / s.seats, 1) AS boarded_pct\nFROM flights f\n         JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure\n         JOIN (SELECT airplane_code, COUNT(*) AS seats FROM seats GROUP BY airplane_code) s ON s.airplane_code = r.airplane_code\n         LEFT JOIN boarding_passes bp ON bp.flight_id = f.flight_id\nWHERE f.status = 'Arrived'\n  AND f.scheduled_departure >= {UTC('2025-10-01')}\n  AND f.scheduled_departure < {UTC('2025-10-02')}\nGROUP BY f.flight_id, f.route_no, r.airplane_code, s.seats\nORDER BY 100.0 * COUNT(bp.boarding_no) / s.seats DESC, f.flight_id\nLIMIT 5")
fix('DEMODB_SCHEMA_I_02', 'both', 'it counted every boarding pass, the checked-in but not boarded too',
    request=["For the flights scheduled in the first seven days from 2025-10-01, count the passengers boarded, the boarding passes with a boarding number, by the departure airport of the flight's route, and keep the ten airports with the most.",
             "Show the code, the name and the count, the most first; airports with the same count are ordered by code.",
             "Four tables: `boarding_passes`, `flights`, `routes` on a range containment, and the `airports` view for the name."],
    sql=f"SELECT a.airport_code, a.airport_name, COUNT(*) AS boarded\nFROM boarding_passes bp\n         JOIN flights f ON f.flight_id = bp.flight_id\n         JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure\n         JOIN airports a ON a.airport_code = r.departure_airport\nWHERE f.scheduled_departure >= {UTC('2025-10-01')}\n  AND f.scheduled_departure < {UTC('2025-10-08')}\n  AND bp.boarding_no IS NOT NULL\nGROUP BY a.airport_code, a.airport_name\nORDER BY boarded DESC, a.airport_code\nLIMIT 10")
fix('DEMODB_BOARDING_PASSES_I_01', 'Claude', 'the title says boarded, but it counted every pass, the checked-in but not boarded too',
    request=["Count the passengers who boarded, the boarding passes with a boarding number, of each `seat_no`, over all flights, and keep the five with the most; seats with the same count are ordered by `seat_no`."],
    sql="SELECT seat_no, COUNT(*) AS boarded\nFROM boarding_passes\nWHERE boarding_no IS NOT NULL\nGROUP BY seat_no\nORDER BY boarded DESC, seat_no\nLIMIT 5")
fix('DEMODB_SCHEMA_B_03', 'both', 'a regclass sorts by its OID, not by the name it prints',
    request=["List the foreign keys of the schema from `pg_constraint`: the table, the constraint's name and its definition, ordered by the table's name and then by the constraint's.",
             "`contype` is `f` for a foreign key, and `pg_get_constraintdef` writes the definition out; a `regclass` sorts by its OID, so it is cast to `text`."],
    sql="SELECT conrelid::regclass::text AS table_name, conname, PG_GET_CONSTRAINTDEF(oid) AS definition\nFROM pg_constraint\nWHERE connamespace = 'bookings'::regnamespace\n  AND contype = 'f'\nORDER BY table_name, conname")
fix('DEMODB_SCHEMA_A_03', 'both', "UNION dedups (airport, step), so step 2 also held the airports one flight away, and SVO; Claude's fewest-flights count, over Codex's request that described the old counts",
    request=["Starting from `SVO`, follow the routes from departure to arrival airport.",
             "Count the airports reachable with one flight, and those reachable with two but not with one; `SVO` itself is not counted.",
             "A recursive query over `routes`, then each airport at its fewest flights."],
    sql="WITH RECURSIVE hops AS (SELECT 'SVO'::bpchar AS airport, 0 AS flights\n                        UNION\n                        SELECT r.arrival_airport, h.flights + 1\n                        FROM hops h\n                                 JOIN routes r ON r.departure_airport = h.airport\n                        WHERE h.flights < 2)\nSELECT flights, COUNT(*) AS airports\nFROM (SELECT airport, MIN(flights) AS flights\n      FROM hops\n      GROUP BY airport) a\nWHERE flights > 0\nGROUP BY flights\nORDER BY flights")
fix('DEMODB_SCHEMA_I_05', 'both', 'two flights from SVO may leave at the same minute; flight_id breaks the tie',
    request=["For the flights of <<DEMODB_TIMETABLE_B_01>>, the ones from `SVO` scheduled in the 24 hours from `bookings.now()`, count the passengers holding a segment, and the seats of the flight's airplane.",
             "Show the flight, the destination, the local departure time, the airplane, the passengers and the seats, by departure and then by `flight_id`.",
             "A `LEFT JOIN` keeps a flight nobody booked, with a `COUNT(s.ticket_no)` of 0; a correlated scalar subquery counts the seats."],
    sql="SELECT t.flight_id,\n       t.arrival_airport,\n       t.scheduled_departure_local,\n       t.airplane_code,\n       COUNT(s.ticket_no)                                                       AS passengers,\n       (SELECT COUNT(*) FROM seats st WHERE st.airplane_code = t.airplane_code) AS seats\nFROM timetable t\n         LEFT JOIN segments s ON s.flight_id = t.flight_id\nWHERE t.departure_airport = 'SVO'\n  AND t.scheduled_departure >= bookings.now()\n  AND t.scheduled_departure < bookings.now() + INTERVAL '24 hours'\nGROUP BY t.flight_id, t.arrival_airport, t.scheduled_departure, t.scheduled_departure_local, t.airplane_code\nORDER BY t.scheduled_departure, t.flight_id")
fix('DEMODB_BOOKINGS_A_01', 'Codex', 'the inner joins hid a booking with no ticket or no priced segment, which should fail the check',
    request=["A booking's `total_amount` should be the sum of the prices of the segments of its tickets.",
             "Join the three tables with outer joins, group by booking, and count the bookings whose total differs from the sum, an empty sum counting as `0`.",
             "A `HAVING` comparing a column of the group with an aggregate; the count is of the groups."],
    sql="SELECT COUNT(*) AS bookings\nFROM (SELECT b.book_ref\n      FROM bookings b\n               LEFT JOIN tickets t ON t.book_ref = b.book_ref\n               LEFT JOIN segments s ON s.ticket_no = t.ticket_no\n      GROUP BY b.book_ref, b.total_amount\n      HAVING b.total_amount <> COALESCE(SUM(s.price), 0)) x")
fix('DEMODB_BOOKINGS_B_01', 'Codex', 'book_date is not unique; book_ref breaks the tie',
    request=["Find the bookings made in the first minute of the data, from 2025-09-01 00:00 UTC up to but not including 00:01.",
             "Show the whole rows, ordered by `book_date`, then by `book_ref`."],
    sql="SELECT *\nFROM bookings\nWHERE book_date >= TIMESTAMPTZ '2025-09-01 00:00:00+00'\n  AND book_date < TIMESTAMPTZ '2025-09-01 00:01:00+00'\nORDER BY book_date, book_ref")
fix('DEMODB_FLIGHTS_I_04', 'Claude', "::date cast every row, in the session's zone; a half-open range on the UTC day of bookings.now()",
    request=["The database's today is the UTC day of `bookings.now()`.",
             "Find the flights scheduled to depart today, and join each to the row of `routes` valid at its scheduled departure.",
             "Show the flight, the route, the two airports, the scheduled departure and the status, ordered by the scheduled departure and then by `flight_id`.",
             "A half-open range on the timestamp, not a cast of each row to a date."],
    sql="SELECT f.flight_id, f.route_no, r.departure_airport, r.arrival_airport, f.scheduled_departure, f.status\nFROM flights f\n         JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure\nWHERE f.scheduled_departure >= DATE_TRUNC('day', bookings.now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'\n  AND f.scheduled_departure < (DATE_TRUNC('day', bookings.now() AT TIME ZONE 'UTC') + INTERVAL '1 day') AT TIME ZONE 'UTC'\nORDER BY f.scheduled_departure, f.flight_id")
fix('DEMODB_SEGMENTS_A_01', 'Claude', "the price check allows 0, and a cheapest Economy price of 0 divided by zero; Claude's condition over Codex's separate check",
    request=["For each flight sold in both fare conditions, with an Economy price above zero, divide the cheapest Business price by the cheapest Economy price, to two decimals.",
             "Keep the five flights with the largest ratio; flights with the same ratio are ordered by `flight_id`.",
             "Show the flight, the two prices and the ratio.",
             "Conditional aggregates with `FILTER`, in the select and in the `HAVING`."],
    sql="SELECT flight_id,\n       MIN(price) FILTER (WHERE fare_conditions = 'Economy')  AS economy,\n       MIN(price) FILTER (WHERE fare_conditions = 'Business') AS business,\n       ROUND(MIN(price) FILTER (WHERE fare_conditions = 'Business') / MIN(price) FILTER (WHERE fare_conditions = 'Economy'), 2) AS ratio\nFROM segments\nGROUP BY flight_id\nHAVING MIN(price) FILTER (WHERE fare_conditions = 'Economy') > 0\n   AND COUNT(*) FILTER (WHERE fare_conditions = 'Business') > 0\nORDER BY ratio DESC, flight_id\nLIMIT 5")
fix('DEMODB_FLIGHTS_A_02', 'Claude', "'from 2025-10-01' had no lower bound; the days are UTC days",
    request=["Count the flights scheduled on each of the seven days from 2025-10-01, UTC, and add a running total, day by day.",
             "A group by the UTC date, and a window `SUM` over the ordered days."],
    sql=f"SELECT (scheduled_departure AT TIME ZONE 'UTC')::date                         AS day,\n       COUNT(*)                                                         AS flights,\n       SUM(COUNT(*)) OVER (ORDER BY (scheduled_departure AT TIME ZONE 'UTC')::date) AS running_total\nFROM flights\nWHERE scheduled_departure >= {UTC('2025-10-01')}\n  AND scheduled_departure < {UTC('2025-10-08')}\nGROUP BY day\nORDER BY day")
add('DEMODB_FLIGHTS_I_05', 'Claude', 'several exercises rely on status agreeing with the actual times, which no constraint enforces',
    title='the flights whose status disagrees with their actual times',
    request=["Find the flights whose status does not match their actual times: `Arrived` with no actual arrival, `Departed` with no actual departure or with an actual arrival, or any other status with an actual departure.",
             "Count them by status; the check passes when nothing comes back."],
    sql="SELECT status, COUNT(*) AS flights\nFROM flights\nWHERE (status = 'Arrived' AND actual_arrival IS NULL)\n   OR (status = 'Departed' AND (actual_departure IS NULL OR actual_arrival IS NOT NULL))\n   OR (status NOT IN ('Arrived', 'Departed') AND actual_departure IS NOT NULL)\nGROUP BY status\nORDER BY status")
add('DEMODB_TICKETS_I_05', 'both', 'the passenger exercises take passenger_id as the person, which nothing ties to one name',
    title='the passenger ids recorded under more than one name',
    request=["The exercises on passengers take `passenger_id` as the person; nothing ties an id to one `passenger_name`.",
             "Find the ids recorded with more than one name, with how many names, ordered by `passenger_id`; the check passes when nothing comes back."],
    sql="SELECT passenger_id, COUNT(DISTINCT passenger_name) AS names\nFROM tickets\nGROUP BY passenger_id\nHAVING COUNT(DISTINCT passenger_name) > 1\nORDER BY passenger_id")
add('DEMODB_BOOKINGS_B_04', 'Claude', "no exercise reads a page past the first, the OFFSET of the module's paging rule",
    title='the second page of the bookings of 2025-10-01',
    request=["Order the bookings made on 2025-10-01, UTC, by `book_date` and then by `book_ref`, twenty to a page, and show the second page, the whole rows.",
             "`book_ref` makes the order total, so each page is fixed."],
    sql="SELECT *\nFROM bookings\nWHERE book_date >= TIMESTAMPTZ '2025-10-01 00:00:00+00'\n  AND book_date < TIMESTAMPTZ '2025-10-02 00:00:00+00'\nORDER BY book_date, book_ref\nLIMIT 20 OFFSET 20")
add('DEMODB_SCHEMA_B_06', 'Codex', 'a simple join and count over the sales data, a question operations asks',
    title='the sold segments of the cancelled flights',
    request=["Count the sold segments, the seats sold to a passenger, of the flights whose status is `Cancelled`."],
    sql="SELECT COUNT(*) AS affected_segments\nFROM segments s\n         JOIN flights f ON f.flight_id = s.flight_id\nWHERE f.status = 'Cancelled'")
add('DEMODB_SCHEMA_I_06', 'Codex', 'the routes do not overlap, but nothing makes a flight match one; every join on validity @> scheduled_departure assumes it',
    title='the flights with no route valid at their departure',
    request=["The exercises join a flight to the row of `routes` valid at its scheduled departure; nothing in the schema says there is one.",
             "Find the flights with none, ordered by departure and then by `flight_id`; the check passes when nothing comes back."],
    sql="SELECT f.flight_id, f.route_no, f.scheduled_departure\nFROM flights f\nWHERE NOT EXISTS (SELECT 1\n                  FROM routes r\n                  WHERE r.route_no = f.route_no\n                    AND r.validity @> f.scheduled_departure)\nORDER BY f.scheduled_departure, f.flight_id")
add('DEMODB_SCHEMA_I_07', 'Claude', "nothing relates book_date to the flights booked, the whole foreign-key chain from bookings to flights",
    title='how far ahead the bookings were made',
    request=["For each booking, the time ahead is the scheduled departure of its first flight minus the time it was made.",
             "Show the shortest, the average, to the hour, and the longest."],
    sql="SELECT MIN(ahead)                     AS shortest,\n       DATE_TRUNC('hour', AVG(ahead)) AS average,\n       MAX(ahead)                     AS longest\nFROM (SELECT b.book_ref, MIN(f.scheduled_departure) - b.book_date AS ahead\n      FROM bookings b\n               JOIN tickets t ON t.book_ref = b.book_ref\n               JOIN segments s ON s.ticket_no = t.ticket_no\n               JOIN flights f ON f.flight_id = s.flight_id\n      GROUP BY b.book_ref, b.book_date) x")
add('DEMODB_SCHEMA_I_08', 'Codex', "the seat totals are used, but never the cabin mix beside the model's range and speed",
    title='the seats of each airplane model, by fare conditions',
    request=["Show every airplane model's code, name, range and speed, with its seats in all and in each fare condition, ordered by code.",
             "An outer join keeps a model without seats; `FILTER` counts each condition."],
    sql="SELECT a.airplane_code,\n       a.model,\n       a.range,\n       a.speed,\n       COUNT(s.seat_no)                                                 AS seats,\n       COUNT(s.seat_no) FILTER (WHERE s.fare_conditions = 'Economy')  AS economy,\n       COUNT(s.seat_no) FILTER (WHERE s.fare_conditions = 'Comfort')  AS comfort,\n       COUNT(s.seat_no) FILTER (WHERE s.fare_conditions = 'Business') AS business\nFROM airplanes a\n         LEFT JOIN seats s ON s.airplane_code = a.airplane_code\nGROUP BY a.airplane_code, a.model, a.range, a.speed\nORDER BY a.airplane_code")
add('DEMODB_SCHEMA_I_09', 'Codex', "the timetable's local times and the airports' time zones answer a departure board's question",
    title="today's departures, in each airport's own day",
    request=["Show the flights departing today, by the date of `bookings.now()` in the departure airport's own time zone.",
             "Show the airport, its name and time zone, the flight, the destination and the local departure, ordered by airport, local departure and `flight_id`.",
             "`AT TIME ZONE` with the airport's zone gives its local date."],
    sql="SELECT a.airport_code,\n       a.airport_name,\n       a.timezone,\n       t.flight_id,\n       t.arrival_airport,\n       t.scheduled_departure_local\nFROM timetable t\n         JOIN airports a ON a.airport_code = t.departure_airport\nWHERE t.scheduled_departure_local::date = (bookings.now() AT TIME ZONE a.timezone)::date\nORDER BY a.airport_code, t.scheduled_departure_local, t.flight_id")
add('DEMODB_SCHEMA_I_10', 'Codex', 'the unique key on booking, passenger and outbound pairs the two directions, which no exercise uses',
    title='the outbound and return tickets of one passenger in one booking',
    request=["A booking may hold, for one passenger, an outbound and a return ticket.",
             "List the passengers with both in the same booking: the booking, its date, the `passenger_id` and the two ticket numbers, ordered by booking and `passenger_id`."],
    sql="SELECT b.book_ref,\n       b.book_date,\n       o.passenger_id,\n       o.ticket_no AS outbound_ticket,\n       i.ticket_no AS return_ticket\nFROM bookings b\n         JOIN tickets o ON o.book_ref = b.book_ref AND o.outbound\n         JOIN tickets i ON i.book_ref = o.book_ref AND i.passenger_id = o.passenger_id AND NOT i.outbound\nORDER BY b.book_ref, o.passenger_id")
add('DEMODB_SCHEMA_A_05', 'both', 'DEMODB_SCHEMA_A_04 assumes a later segment departs from where the earlier one arrived, after it arrived; nothing enforces either',
    title='the segments which do not connect to the previous one of their ticket',
    request=["For each segment but a ticket's first, compare it with the previous segment of the ticket, in order of scheduled departure.",
             "Count the segments that depart from another airport than the previous one arrived at, and those scheduled to depart before the previous one arrives; the check passes when both are `0`."],
    sql="SELECT COUNT(*) FILTER (WHERE departure_airport <> previous_airport)  AS elsewhere,\n       COUNT(*) FILTER (WHERE scheduled_departure < previous_arrival) AS overlapping\nFROM (SELECT r.departure_airport,\n             f.scheduled_departure,\n             LAG(r.arrival_airport) OVER w   AS previous_airport,\n             LAG(f.scheduled_arrival) OVER w AS previous_arrival\n      FROM segments s\n               JOIN flights f ON f.flight_id = s.flight_id\n               JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure\n      WINDOW w AS (PARTITION BY s.ticket_no ORDER BY f.scheduled_departure, f.flight_id)) c")
add('DEMODB_SCHEMA_A_06', 'Codex', 'the composite key from boarding_passes to segments, and a missing pass told from a pass with no boarding time',
    title='the passengers still to board the flights now boarding',
    request=["For the flights whose status is `Boarding`, list the sold segments whose passenger has no boarding time yet, those with no boarding pass included.",
             "Show the flight, the ticket, the passenger's name, the seat and the boarding number, ordered by flight and ticket."],
    sql="SELECT f.flight_id, s.ticket_no, t.passenger_name, bp.seat_no, bp.boarding_no\nFROM flights f\n         JOIN segments s ON s.flight_id = f.flight_id\n         JOIN tickets t ON t.ticket_no = s.ticket_no\n         LEFT JOIN boarding_passes bp ON bp.ticket_no = s.ticket_no AND bp.flight_id = s.flight_id\nWHERE f.status = 'Boarding'\n  AND bp.boarding_time IS NULL\nORDER BY f.flight_id, s.ticket_no")
rm('DEMODB_SEGMENTS_I_03', 'Claude', "DEMODB_SEGMENTS_I_04 with > 2 in place of > 1; DEMODB_SCHEMA_A_01 shows the tickets with the most segments")

# ---------------------------------------------------------------------------------------- the UTC sweep, module-wide
LIT = re.compile(r"(?<!TIMESTAMPTZ )(?<!TIMESTAMP )'(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2})(?::(\d{2}))?)?'")
TZCOL = r"((?:\w+\.)?(?:scheduled_departure|scheduled_arrival|actual_departure|actual_arrival|book_date))"
CHAR = re.compile(rf"TO_CHAR\({TZCOL},")
def utc(sql):
    sql = LIT.sub(lambda m: f"TIMESTAMPTZ '{m[1]} {m[2] or '00:00'}:{m[3] or '00'}+00'", sql)
    return CHAR.sub(lambda m: f"TO_CHAR({m[1]} AT TIME ZONE 'UTC',", sql)
fixed = {c['id'] for c in C}
swept = []
for f in sorted(glob.glob(f'{MOD}/*/*.sql')):
    t = open(f).read()
    for m in re.finditer(r'(?ms)^-- -+ (DEMODB_[A-Z0-9_]+)\n(.*?)^;$', t):
        stmt = '\n'.join(l for l in m[2].split('\n') if not l.startswith('--')).strip()
        if m[1] in fixed or not (LIT.search(stmt) or CHAR.search(stmt)) or not re.search(r'(scheduled_|actual_|book_date)', stmt):
            continue
        C.append(dict(op='fix', id=m[1], _src='both', _why="the UTC sweep: a date bound against a timestamptz, or a TO_CHAR of one, is read in the session's zone; written as TIMESTAMPTZ '... +00', and AT TIME ZONE 'UTC'",
                      sql=utc(stmt), rerun=True))
        swept.append(m[1])
for c in C:  # the explicit ones too, where a bound is still bare
    if 'sql' in c and c['id'] != 'DEMODB_TIMETABLE_A_02':
        c['sql'] = utc(c['sql'])
json.dump({'module': 'postgresql-demodb-persistence', 'changes': C}, open('decisions.json', 'w'), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter(c['op'] for c in C), 'swept', swept)
