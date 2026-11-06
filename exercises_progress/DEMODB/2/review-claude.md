# DEMODB batch 2 — Claude's review

### fix DEMODB_FLIGHTS_A_03
- section: FLIGHTS   tier: Advanced
- title: the five fullest flights of the first day
- why: `COUNT(bp.ticket_no)` counts every boarding pass, including those with a `NULL` `boarding_no` (checked in, not boarded, as BOARDING_PASSES_B_02 and I_04 define it), so `boarded` and the share overstate the seats boarded.
- request: For the flights scheduled on 2025-10-01 that arrived, count the passengers boarded (the boarding passes with a boarding number) and the seats of the flight's airplane, and keep the five with the highest share of seats boarded; flights with the same share are ordered by `flight_id`. Show the flight, the route, the airplane, the two counts and the share as a percentage to one decimal.
- sql:
    ```sql
    SELECT f.flight_id,
           f.route_no,
           r.airplane_code,
           COUNT(bp.boarding_no)                                              AS boarded,
           s.seats,
           ROUND(100.0 * COUNT(bp.boarding_no) / s.seats, 1)                  AS boarded_pct
    FROM flights f
             JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure
             JOIN (SELECT airplane_code, COUNT(*) AS seats FROM seats GROUP BY airplane_code) s
                  ON s.airplane_code = r.airplane_code
             JOIN boarding_passes bp ON bp.flight_id = f.flight_id
    WHERE f.status = 'Arrived'
      AND f.scheduled_departure >= '2025-10-01'
      AND f.scheduled_departure < '2025-10-02'
    GROUP BY f.flight_id, f.route_no, r.airplane_code, s.seats
    ORDER BY boarded_pct DESC, f.flight_id
    LIMIT 5
    ```

### fix DEMODB_SCHEMA_I_02
- section: SCHEMA   tier: Intermediate
- title: the ten airports with the most passengers boarded in the first week
- why: The request counts passengers boarded, but the SQL counts every boarding pass, the ones with a `NULL` `boarding_no` (not boarded) too.
- request: For the flights scheduled in the first seven days from 2025-10-01, count the passengers boarded, the boarding passes with a boarding number, by the departure airport of the flight's route, and keep the ten airports with the most. Show the code, the name and the count, the most first; airports with the same count are ordered by code.
- sql:
    ```sql
    SELECT a.airport_code, a.airport_name, COUNT(*) AS boarded
    FROM boarding_passes bp
             JOIN flights f ON f.flight_id = bp.flight_id
             JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure
             JOIN airports a ON a.airport_code = r.departure_airport
    WHERE f.scheduled_departure >= '2025-10-01'
      AND f.scheduled_departure < '2025-10-08'
      AND bp.boarding_no IS NOT NULL
    GROUP BY a.airport_code, a.airport_name
    ORDER BY boarded DESC, a.airport_code
    LIMIT 10
    ```

### fix DEMODB_BOARDING_PASSES_I_01
- section: BOARDING_PASSES   tier: Intermediate
- title: the five seats boarded the most
- why: The title says "boarded" but the SQL counts every pass, including the checked-in-but-not-boarded ones the section itself separates by `boarding_no IS NULL`.
- request: Count the boarding passes with a boarding number, the passengers who boarded, of each `seat_no`, over all flights, and keep the five with the most; seats with the same count are ordered by `seat_no`.
- sql:
    ```sql
    SELECT seat_no, COUNT(*) AS boarded
    FROM boarding_passes
    WHERE boarding_no IS NOT NULL
    GROUP BY seat_no
    ORDER BY boarded DESC, seat_no
    LIMIT 5
    ```

### fix DEMODB_SCHEMA_B_03
- section: SCHEMA   tier: Basic
- title: the foreign keys, and what they reference
- why: `ORDER BY table_name` sorts the `regclass` output column by its OID, not by the table's name, so the rows are not "ordered by table" as the request says.
- request: List the foreign keys of the schema from `pg_constraint`: the table, the constraint's name and its definition, ordered by the table's name and then by the constraint's name.
- sql:
    ```sql
    SELECT conrelid::regclass AS table_name, conname, PG_GET_CONSTRAINTDEF(oid) AS definition
    FROM pg_constraint
    WHERE connamespace = 'bookings'::regnamespace
      AND contype = 'f'
    ORDER BY conrelid::regclass::text, conname
    ```

### fix DEMODB_SCHEMA_A_03
- section: SCHEMA   tier: Advanced
- title: how many airports are one and two routes away from Sheremetyevo
- why: `UNION` dedups only (airport, step) pairs, so the step-2 count also holds the airports already one flight away and `SVO` itself (every return route), and the step-0 row counts `SVO`; the counts do not answer "how many airports are one and two routes away". Count each airport at its fewest flights, without `SVO`.
- request: Starting from `SVO`, follow the routes from departure to arrival airport. Count the airports reachable with one flight, and those reachable with two but not with one; `SVO` itself is not counted.
- sql:
    ```sql
    WITH RECURSIVE hops AS (SELECT 'SVO'::bpchar AS airport, 0 AS flights
                            UNION
                            SELECT r.arrival_airport, h.flights + 1
                            FROM hops h
                                     JOIN routes r ON r.departure_airport = h.airport
                            WHERE h.flights < 2)
    SELECT flights, COUNT(*) AS airports
    FROM (SELECT airport, MIN(flights) AS flights
          FROM hops
          GROUP BY airport) a
    WHERE flights > 0
    GROUP BY flights
    ORDER BY flights
    ```

### fix DEMODB_SCHEMA_I_05
- section: SCHEMA   tier: Intermediate
- title: the passengers and the seats of the flights from Sheremetyevo in the next 24 hours
- why: `ORDER BY t.scheduled_departure_local` alone is unstable: two flights from `SVO` can leave at the same minute for different destinations.
- request: For the flights from `SVO` scheduled in the 24 hours from `bookings.now()`, count the passengers holding a segment, and the seats of the flight's airplane. Show the flight, the destination, the local departure time, the airplane, the passengers and the seats, by departure and then by `flight_id`.
- sql:
    ```sql
    SELECT t.flight_id,
           t.arrival_airport,
           t.scheduled_departure_local,
           t.airplane_code,
           COUNT(s.ticket_no)                                                       AS passengers,
           (SELECT COUNT(*) FROM seats st WHERE st.airplane_code = t.airplane_code) AS seats
    FROM timetable t
             LEFT JOIN segments s ON s.flight_id = t.flight_id
    WHERE t.departure_airport = 'SVO'
      AND t.scheduled_departure >= bookings.now()
      AND t.scheduled_departure < bookings.now() + INTERVAL '24 hours'
    GROUP BY t.flight_id, t.arrival_airport, t.scheduled_departure_local, t.airplane_code
    ORDER BY t.scheduled_departure_local, t.flight_id
    ```

### fix DEMODB_FLIGHTS_I_04
- section: FLIGHTS   tier: Intermediate
- title: today's flights, with their airports
- why: `f.scheduled_departure::date = ...` casts every row and cannot use a range on the column; the module's own idiom (FLIGHTS_B_01) is a half-open range on the timestamp. The answer is the same, in the same session time zone.
- request: The database's today is the day of `bookings.now()`. Find the flights scheduled to depart today, and join each to the row of `routes` valid at its scheduled departure. Show the flight, the route, the two airports, the scheduled departure and the status, ordered by the scheduled departure and then by `flight_id`.
- sql:
    ```sql
    SELECT f.flight_id, f.route_no, r.departure_airport, r.arrival_airport, f.scheduled_departure, f.status
    FROM flights f
             JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure
    WHERE f.scheduled_departure >= DATE_TRUNC('day', bookings.now())
      AND f.scheduled_departure < DATE_TRUNC('day', bookings.now()) + INTERVAL '1 day'
    ORDER BY f.scheduled_departure, f.flight_id
    ```

### fix DEMODB_SEGMENTS_A_01
- section: SEGMENTS   tier: Advanced
- title: the five flights where Business costs the most over Economy
- why: `segments_price_check` allows a price of 0, and a cheapest Economy price of 0 divides by zero and fails the whole query; requiring the cheapest Economy price to be positive also replaces the Economy `COUNT ... > 0` test.
- request: For each flight sold in both fare conditions, with an Economy price above zero, divide the cheapest Business price by the cheapest Economy price, to two decimals. Keep the five flights with the largest ratio; flights with the same ratio are ordered by `flight_id`. Show the flight, the two prices and the ratio.
- sql:
    ```sql
    SELECT flight_id,
           MIN(price) FILTER (WHERE fare_conditions = 'Economy')                                                          AS economy,
           MIN(price) FILTER (WHERE fare_conditions = 'Business')                                                         AS business,
           ROUND(MIN(price) FILTER (WHERE fare_conditions = 'Business') / MIN(price) FILTER (WHERE fare_conditions = 'Economy'), 2) AS ratio
    FROM segments
    GROUP BY flight_id
    HAVING MIN(price) FILTER (WHERE fare_conditions = 'Economy') > 0
       AND COUNT(*) FILTER (WHERE fare_conditions = 'Business') > 0
    ORDER BY ratio DESC, flight_id
    LIMIT 5
    ```

### fix DEMODB_FLIGHTS_A_02
- section: FLIGHTS   tier: Advanced
- title: the flights of each day of the first week, and their running total
- why: The request says "from 2025-10-01" but the SQL has no lower bound, so it relies on there being no earlier flight; the half-open range should be written out, as FLIGHTS_B_01 does.
- request: Count the flights scheduled on each of the seven days from 2025-10-01, and add a running total, day by day.
- sql:
    ```sql
    SELECT scheduled_departure::date                                   AS day,
           COUNT(*)                                                    AS flights,
           SUM(COUNT(*)) OVER (ORDER BY scheduled_departure::date)     AS running_total
    FROM flights
    WHERE scheduled_departure >= '2025-10-01'
      AND scheduled_departure < '2025-10-08'
    GROUP BY scheduled_departure::date
    ORDER BY day
    ```

### add DEMODB_FLIGHTS_I_05
- section: FLIGHTS   tier: Intermediate
- title: the flights whose status disagrees with their actual times
- why: FLIGHTS_B_05 ("every one of them has the status Departed"), I_02 and A_01 rely on `status` agreeing with `actual_departure` / `actual_arrival`, which no constraint enforces; this check guards that fact.
- request: Find the flights whose status does not match their actual times: `Arrived` with no actual arrival, `Departed` with no actual departure or with an actual arrival, or any other status with an actual departure. Count them by status; there should be none.
- sql:
    ```sql
    SELECT status, COUNT(*) AS flights
    FROM flights
    WHERE (status = 'Arrived' AND actual_arrival IS NULL)
       OR (status = 'Departed' AND (actual_departure IS NULL OR actual_arrival IS NOT NULL))
       OR (status NOT IN ('Arrived', 'Departed') AND actual_departure IS NOT NULL)
    GROUP BY status
    ORDER BY status
    ```

### add DEMODB_TICKETS_I_05
- section: TICKETS   tier: Intermediate
- title: the passenger ids that carry more than one name
- why: TICKETS_I_01 and I_04, and TICKETS_A_01, take `passenger_id` as the person, but nothing ties a `passenger_id` to one `passenger_name`; this check guards that fact.
- request: Count the `passenger_id` values that appear on tickets with more than one `passenger_name`; there should be none.
- sql:
    ```sql
    SELECT COUNT(*) AS passengers
    FROM (SELECT passenger_id
          FROM tickets
          GROUP BY passenger_id
          HAVING COUNT(DISTINCT passenger_name) > 1) p
    ```

### add DEMODB_SCHEMA_I_06
- section: SCHEMA   tier: Intermediate
- title: how far ahead the bookings were made
- why: Nothing relates `bookings.book_date` to the flights booked, the most natural question of a booking; it walks the whole foreign-key chain from `bookings` to `flights`.
- request: For each booking, the time ahead is the scheduled departure of its first flight minus the time it was made. Show the shortest, the average, to the hour, and the longest.
- sql:
    ```sql
    SELECT MIN(ahead)                       AS shortest,
           DATE_TRUNC('hour', AVG(ahead))   AS average,
           MAX(ahead)                       AS longest
    FROM (SELECT b.book_ref, MIN(f.scheduled_departure) - b.book_date AS ahead
          FROM bookings b
                   JOIN tickets t ON t.book_ref = b.book_ref
                   JOIN segments s ON s.ticket_no = t.ticket_no
                   JOIN flights f ON f.flight_id = s.flight_id
          GROUP BY b.book_ref, b.book_date) x
    ```

### add DEMODB_BOOKINGS_B_04
- section: BOOKINGS   tier: Basic
- title: the second page of the bookings of 2025-10-01
- why: No exercise reads a page past the first, the `OFFSET` (and JPA's `setFirstResult`) the module's paging rule provides for; it also needs a total order, `book_date` then the key.
- request: Order the bookings made on 2025-10-01 by `book_date` and then by `book_ref`, twenty to a page, and show the second page, the whole rows.
- sql:
    ```sql
    SELECT *
    FROM bookings
    WHERE book_date >= '2025-10-01'
      AND book_date < '2025-10-02'
    ORDER BY book_date, book_ref
    LIMIT 20 OFFSET 20
    ```

### add DEMODB_SCHEMA_A_05
- section: SCHEMA   tier: Advanced
- title: the segments that do not connect to the previous one of their ticket
- why: SCHEMA_A_04 states that a later segment always departs from the airport the earlier one arrived at, and its layovers assume it leaves after that arrival; no constraint enforces either, so this check guards them.
- request: For each segment but a ticket's first, compare it with the previous segment of the ticket, in order of scheduled departure. Count the segments that depart from another airport than the previous one arrived at, and those scheduled to depart before the previous one arrives; there should be none of either.
- sql:
    ```sql
    SELECT COUNT(*) FILTER (WHERE departure_airport <> previous_airport)  AS elsewhere,
           COUNT(*) FILTER (WHERE scheduled_departure < previous_arrival) AS overlapping
    FROM (SELECT r.departure_airport,
                 f.scheduled_departure,
                 LAG(r.arrival_airport) OVER w     AS previous_airport,
                 LAG(f.scheduled_arrival) OVER w   AS previous_arrival
          FROM segments s
                   JOIN flights f ON f.flight_id = s.flight_id
                   JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure
          WINDOW w AS (PARTITION BY s.ticket_no ORDER BY f.scheduled_departure)) c
    ```

### remove DEMODB_SEGMENTS_I_03
- section: SEGMENTS   tier: Intermediate
- title: how many tickets have more than two segments
- why: It is SEGMENTS_I_04 with `> 2` in place of `> 1` and without the `BOOL_AND`: the same grouped `HAVING COUNT(*)` subquery counted outside, and SCHEMA_A_01 already shows the tickets with the most segments. SEGMENTS Intermediate stays populated by I_01, I_02 and I_04.
