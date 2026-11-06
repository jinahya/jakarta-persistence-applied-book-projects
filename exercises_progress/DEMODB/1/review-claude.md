# DEMODB batch 1 — Claude's review

### fix DEMODB_SEATS_A_01
- section: SEATS   tier: Advanced
- title: the empty seats of the flight 1
- why: The SQL hard-codes `'7M7'`, the request's own claim about flight 1, so the query never reads which airplane the flight uses. The airplane comes from the route row valid at the flight's departure, which `timetable` already resolves. Without that step the exercise is a Basic anti-join, not an Advanced one.
- request: Find the seats of the airplane that flies the flight `1` that no boarding pass of that flight holds. Show the seat and its fare conditions, ordered by `seat_no`.
- sql:
    SELECT s.seat_no, s.fare_conditions
    FROM timetable t
             JOIN seats s ON s.airplane_code = t.airplane_code
    WHERE t.flight_id = 1
      AND NOT EXISTS (SELECT 1
                      FROM boarding_passes bp
                      WHERE bp.flight_id = t.flight_id
                        AND bp.seat_no = s.seat_no)
    ORDER BY s.seat_no

### fix DEMODB_TIMETABLE_B_02
- section: TIMETABLE   tier: Basic
- title: the flights of the route PG0078 on the first day, in local time
- why: `'2025-10-01'` compared with a `timestamptz` is read in the session's `TimeZone`. The database doesn't set one, and PgJDBC sends the JVM's zone, so the JPA/Criteria twins can return different rows than psql. Say "UTC day" and write the offset.
- request: Find the flights of the route `PG0078` scheduled to depart on 2025-10-01, UTC; show the flight, the two airports, the scheduled departure in UTC and local time, and the local scheduled arrival, ordered by the scheduled departure.
- sql:
    SELECT flight_id, departure_airport, arrival_airport, scheduled_departure, scheduled_departure_local, scheduled_arrival_local
    FROM timetable
    WHERE route_no = 'PG0078'
      AND scheduled_departure >= TIMESTAMPTZ '2025-10-01 00:00:00+00'
      AND scheduled_departure < TIMESTAMPTZ '2025-10-02 00:00:00+00'
    ORDER BY scheduled_departure

### fix DEMODB_TIMETABLE_A_02
- section: TIMETABLE   tier: Advanced
- title: the connections at Sheremetyevo on the first day
- why: Same session-time-zone dependency as TIMETABLE_B_02: `'2025-10-01'` against `scheduled_arrival` moves the day with the client's zone, and with it the set of arriving flights and the first ten.
- request: For each flight scheduled to arrive at `SVO` on 2025-10-01, UTC, find the flights departing from `SVO` between one and four hours after its scheduled arrival; show the arriving flight, the departing flight, its destination and the layover, ordered by the two flights; the first ten.
- sql:
    SELECT a.flight_id                                 AS arriving,
           d.flight_id                                 AS departing,
           d.arrival_airport                           AS destination,
           d.scheduled_departure - a.scheduled_arrival AS layover
    FROM timetable a
             JOIN timetable d ON d.departure_airport = a.arrival_airport
        AND d.scheduled_departure BETWEEN a.scheduled_arrival + INTERVAL '1 hour' AND a.scheduled_arrival + INTERVAL '4 hours'
    WHERE a.arrival_airport = 'SVO'
      AND a.scheduled_arrival >= TIMESTAMPTZ '2025-10-01 00:00:00+00'
      AND a.scheduled_arrival < TIMESTAMPTZ '2025-10-02 00:00:00+00'
    ORDER BY a.flight_id, d.flight_id
    LIMIT 10

### fix DEMODB_TIMETABLE_I_03
- section: TIMETABLE   tier: Intermediate
- title: the flights that arrived late, by month
- why: `TO_CHAR(scheduled_arrival, 'YYYY-MM')` takes the month in the session's zone, so a flight near midnight on a month boundary moves between months. The two counts also define "arrived" in different ways: one uses `status = 'Arrived'`, the other uses a non-NULL `actual_arrival`. Count both from `actual_arrival`, the column the late test reads.
- request: Group the flights by the UTC month of their scheduled arrival, and show the month, how many have an actual arrival, and how many of those arrived more than an hour after the scheduled one, in order.
- sql:
    SELECT TO_CHAR(scheduled_arrival AT TIME ZONE 'UTC', 'YYYY-MM')                     AS month,
           COUNT(actual_arrival)                                                        AS arrived,
           COUNT(*) FILTER (WHERE actual_arrival > scheduled_arrival + INTERVAL '1 hour') AS late
    FROM timetable
    GROUP BY month
    ORDER BY month

### fix DEMODB_TIMETABLE_B_01
- section: TIMETABLE   tier: Basic
- title: the flights from Sheremetyevo in the next 24 hours
- why: `ORDER BY scheduled_departure` alone is unstable: several routes can leave SVO at the same minute, and `(route_no, scheduled_departure)` is unique only within a route.
- request: Find the flights from `SVO` whose scheduled departure is within 24 hours after `bookings.now()`; show the flight, the route, the arrival airport, the local departure time and the status, ordered by the scheduled departure and then by flight.
- sql:
    SELECT flight_id, route_no, arrival_airport, scheduled_departure_local, status
    FROM timetable
    WHERE departure_airport = 'SVO'
      AND scheduled_departure >= bookings.now()
      AND scheduled_departure < bookings.now() + INTERVAL '24 hours'
    ORDER BY scheduled_departure, flight_id

### fix DEMODB_AIRPLANES_DATA_A_02
- section: AIRPLANES_DATA   tier: Advanced
- title: the airplanes by the flights they fly
- why: The request counts the flights of each airplane, and `COUNT(f.flight_id)` shows that zeros were meant. The inner joins drop every airplane with no route or no flight, so those zeros never appear. Use outer joins.
- request: Count the flights each airplane flies, zero included: a flight's airplane is the one of the route's row valid at the flight's scheduled departure. Show the code, the English name and the count, the most first, then by `airplane_code`.
- sql:
    SELECT a.airplane_code, a.model ->> 'en' AS model, COUNT(f.flight_id) AS flights
    FROM airplanes_data a
             LEFT JOIN routes r ON r.airplane_code = a.airplane_code
             LEFT JOIN flights f ON f.route_no = r.route_no AND r.validity @> f.scheduled_departure
    GROUP BY a.airplane_code, a.model
    ORDER BY flights DESC, a.airplane_code

### fix DEMODB_AIRPORTS_DATA_A_01
- section: AIRPORTS_DATA   tier: Advanced
- title: the cities with more than one airport
- why: The group key is (city, country), but the sort is `count DESC, city`. Two countries' cities with the same English name and the same count tie, and `LIMIT 10` can cut between them. Add the country to the sort.
- request: Group the airports by city and country, in English, and keep the cities with more than one; show the city, the country, the codes in order and the count, the most first, then by city and country; the first ten.
- sql:
    SELECT city ->> 'en'                                        AS city,
           country ->> 'en'                                     AS country,
           STRING_AGG(airport_code, ', ' ORDER BY airport_code) AS airports,
           COUNT(*)                                             AS count
    FROM airports_data
    GROUP BY city ->> 'en', country ->> 'en'
    HAVING COUNT(*) > 1
    ORDER BY count DESC, city, country
    LIMIT 10

### fix DEMODB_ROUTES_B_03
- section: ROUTES   tier: Basic
- title: the routes flown every day of the week
- why: `CARDINALITY(...) = 7` counts elements, not days. It is correct only if the array never repeats a day or holds a value outside 1–7, and the DDL enforces neither. `@>` asks the question itself: does the array hold every day?
- request: Find the route rows whose `days_of_week` holds all seven days; show the route number, the airports, the departure time and the validity, ordered by `route_no` and then by `validity`.
- sql:
    SELECT route_no, departure_airport, arrival_airport, scheduled_time, validity
    FROM routes
    WHERE days_of_week @> ARRAY [1, 2, 3, 4, 5, 6, 7]
    ORDER BY route_no, validity

### fix DEMODB_ROUTES_A_02
- section: ROUTES   tier: Advanced
- title: the routes with a return route in the same period
- why: "once per pair of airports in each direction" says nothing clear about what one result row is. The SQL gives one row per pair of route numbers, taken from the direction whose departure airport sorts first. The request should say that. The SQL stays the same.
- request: Pair each route with a route flying the opposite direction whose period of validity overlaps its own; show each pair of route numbers once, starting from the airport whose code sorts first, with the two airports, ordered by the two route numbers; the first ten.
- sql:
    SELECT DISTINCT r1.route_no, r2.route_no AS return_route_no, r1.departure_airport, r1.arrival_airport
    FROM routes r1
             JOIN routes r2 ON r2.departure_airport = r1.arrival_airport
        AND r2.arrival_airport = r1.departure_airport
        AND r2.validity && r1.validity
    WHERE r1.departure_airport < r1.arrival_airport
    ORDER BY r1.route_no, r2.route_no
    LIMIT 10

### add DEMODB_ROUTES_A_04
- section: ROUTES   tier: Advanced
- title: the ten longest routes valid today, by great-circle distance
- why: The DDL installs `earthdistance`, and no exercise uses it. The airports' `point`, the airplane's `range` in km and the route's two airport foreign keys meet only here: a three-way join that also checks whether each airplane can fly its route.
- request: For the routes valid at `bookings.now()`, compute the great-circle distance between the two airports in km, and show the route, the two airports, the airplane, its range and the distance, the farthest first, then by route number; the first ten.
- sql:
    SELECT r.route_no,
           r.departure_airport,
           r.arrival_airport,
           r.airplane_code,
           a.range,
           ROUND(((dep.coordinates <@> arr.coordinates) * 1.609344)::numeric) AS distance_km
    FROM routes r
             JOIN airports_data dep ON dep.airport_code = r.departure_airport
             JOIN airports_data arr ON arr.airport_code = r.arrival_airport
             JOIN airplanes_data a ON a.airplane_code = r.airplane_code
    WHERE r.validity @> bookings.now()
    ORDER BY distance_km DESC, r.route_no
    LIMIT 10

### add DEMODB_TIMETABLE_B_03
- section: TIMETABLE   tier: Basic
- title: how many flights of each status
- why: `status` is a CHECK-constrained enum that no exercise reads. It is the first thing a user asks of a timetable, and it shows how the flights split around `bookings.now()`.
- request: Count the flights of each status; show the status and the count, ordered by status.
- sql:
    SELECT status, COUNT(*) AS flights
    FROM timetable
    GROUP BY status
    ORDER BY status

### add DEMODB_TIMETABLE_I_05
- section: TIMETABLE   tier: Intermediate
- title: the ten airports with the longest average departure delay
- why: `actual_departure` is nullable, and no exercise measures a delay. This one adds interval arithmetic on nullable columns, `AVG` over an `interval`, and a `HAVING` that drops airports with too few flights to mean anything.
- request: For the flights that have departed, average the actual minus the scheduled departure by departure airport, keeping the airports with at least 100 such flights; show the airport, the flights and the average delay, the longest first, then by airport; the first ten.
- sql:
    SELECT departure_airport,
           COUNT(*)                                  AS departed,
           AVG(actual_departure - scheduled_departure) AS average_delay
    FROM timetable
    WHERE actual_departure IS NOT NULL
    GROUP BY departure_airport
    HAVING COUNT(*) >= 100
    ORDER BY average_delay DESC, departure_airport
    LIMIT 10

### add DEMODB_ROUTES_I_06
- section: ROUTES   tier: Intermediate
- title: how many routes fly on each day of the week, today
- why: `days_of_week` is tested only with `ANY` and `CARDINALITY`. Turning the array into rows with `UNNEST` is the natural next step, and it answers a real question: which weekday is busiest?
- request: For the routes valid at `bookings.now()`, count the routes flown on each day of the week (1 is Monday); show the day and the count, in order.
- sql:
    SELECT d.day_of_week, COUNT(*) AS routes
    FROM routes r
             CROSS JOIN UNNEST(r.days_of_week) AS d(day_of_week)
    WHERE r.validity @> bookings.now()
    GROUP BY d.day_of_week
    ORDER BY d.day_of_week

### remove DEMODB_AIRPLANES_I_02
- section: AIRPLANES   tier: Intermediate
- title: whether the view agrees with the table
- why: The view is defined as `model ->> bookings.lang()` over the same table, so the query compares that expression with itself and is empty by construction. No user would ask it. AIRPLANES keeps I_01 at this tier.

### remove DEMODB_AIRPORTS_DATA_B_03
- section: AIRPORTS_DATA   tier: Basic
- title: the airports whose code starts with SV
- why: The first letters of an IATA code mean nothing, so no user asks for this. `LIKE` is already taught by AIRPLANES_B_02. AIRPORTS_DATA keeps B_01 and B_02 at this tier.
