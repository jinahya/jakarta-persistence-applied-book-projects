### fix DEMODB_AIRPLANES_DATA_A_02

- section: AIRPLANES_DATA   tier: Advanced
- title: flights per airplane, including zero
- why: The inner joins omit airplanes with no matching flights, although the request asks for each airplane.
- request: Count the flights of every airplane, including zero. Show its code, English model name and count, most flights first, then by code.
- sql:

    ```sql
    SELECT a.airplane_code, a.model ->> 'en' AS model, COUNT(f.flight_id) AS flights
    FROM airplanes_data a
             LEFT JOIN routes r ON r.airplane_code = a.airplane_code
             LEFT JOIN flights f ON f.route_no = r.route_no
        AND r.validity @> f.scheduled_departure
    GROUP BY a.airplane_code, a.model
    ORDER BY flights DESC, a.airplane_code
    ```

### fix DEMODB_TIMETABLE_B_02

- section: TIMETABLE   tier: Basic
- title: PG0078 on the first UTC day
- why: The unzoned date literals depend on the session time zone, and selecting a `timestamptz` directly does not guarantee UTC display.
- request: Find PG0078 flights scheduled to depart on 2025-10-01 UTC. Show the flight, airports, scheduled departure in UTC and airport local time, and scheduled arrival in airport local time, ordered by scheduled departure.
- sql:

    ```sql
    SELECT flight_id,
           departure_airport,
           arrival_airport,
           scheduled_departure AT TIME ZONE 'UTC' AS scheduled_departure_utc,
           scheduled_departure_local,
           scheduled_arrival_local
    FROM timetable
    WHERE route_no = 'PG0078'
      AND scheduled_departure >= TIMESTAMPTZ '2025-10-01 00:00:00+00'
      AND scheduled_departure < TIMESTAMPTZ '2025-10-02 00:00:00+00'
    ORDER BY scheduled_departure
    ```

### fix DEMODB_TIMETABLE_A_02

- section: TIMETABLE   tier: Advanced
- title: connections on Sheremetyevo’s first local day
- why: “On 2025-10-01” needs a time-zone definition. The current bounds use the session zone rather than explicitly selecting the airport’s local day.
- request: For flights scheduled to arrive at SVO on 2025-10-01 in SVO local time, find departures from SVO one to four hours later, inclusive. Show the arriving flight, departing flight, destination and layover; take the first ten ordered by the two flight ids.
- sql:

    ```sql
    SELECT a.flight_id                                 AS arriving,
           d.flight_id                                 AS departing,
           d.arrival_airport                           AS destination,
           d.scheduled_departure - a.scheduled_arrival AS layover
    FROM timetable a
             JOIN timetable d ON d.departure_airport = a.arrival_airport
        AND d.scheduled_departure BETWEEN a.scheduled_arrival + INTERVAL '1 hour'
                                      AND a.scheduled_arrival + INTERVAL '4 hours'
    WHERE a.arrival_airport = 'SVO'
      AND a.scheduled_arrival_local >= TIMESTAMP '2025-10-01 00:00:00'
      AND a.scheduled_arrival_local < TIMESTAMP '2025-10-02 00:00:00'
    ORDER BY a.flight_id, d.flight_id
    LIMIT 10
    ```

### fix DEMODB_TIMETABLE_I_03

- section: TIMETABLE   tier: Intermediate
- title: arrived and late flights by UTC month
- why: Month grouping currently depends on the session time zone. The late count also lacks the status condition used to define the arrived count.
- request: For each UTC month of scheduled arrival, count flights with status Arrived and, among those, flights arriving more than one hour late. Show every represented month in order.
- sql:

    ```sql
    SELECT TO_CHAR(scheduled_arrival AT TIME ZONE 'UTC', 'YYYY-MM') AS month,
           COUNT(*) FILTER (WHERE status = 'Arrived') AS arrived,
           COUNT(*) FILTER (
               WHERE status = 'Arrived'
                 AND actual_arrival > scheduled_arrival + INTERVAL '1 hour'
           ) AS late
    FROM timetable
    GROUP BY month
    ORDER BY month
    ```

### fix DEMODB_ROUTES_A_02

- section: ROUTES   tier: Advanced
- title: route numbers with an overlapping return service
- why: The request alternates between pairing period rows and returning one row per airport pair; the SQL actually returns distinct route-number pairs. State that grain explicitly and complete the ordering.
- request: Find distinct pairs of route numbers serving opposite directions with at least one overlapping validity period. Represent each pair with the alphabetically smaller airport as departure; show both route numbers and airports, taking the first ten ordered by those four columns.
- sql:

    ```sql
    SELECT DISTINCT r1.route_no,
                    r2.route_no AS return_route_no,
                    r1.departure_airport,
                    r1.arrival_airport
    FROM routes r1
             JOIN routes r2 ON r2.departure_airport = r1.arrival_airport
        AND r2.arrival_airport = r1.departure_airport
        AND r2.validity && r1.validity
    WHERE r1.departure_airport < r1.arrival_airport
    ORDER BY r1.route_no, r2.route_no, r1.departure_airport, r1.arrival_airport
    LIMIT 10
    ```

### fix DEMODB_AIRPORTS_DATA_A_01

- section: AIRPORTS_DATA   tier: Advanced
- title: cities with several airports
- why: City alone does not distinguish groups belonging to different countries, making the limited result unstable when counts and city names tie.
- request: Group airports by English city and country, keeping groups with more than one airport. Show city, country, ordered airport codes and count; take the first ten ordered by count descending, city and country.
- sql:

    ```sql
    SELECT city ->> 'en'                                  AS city,
           country ->> 'en'                               AS country,
           STRING_AGG(airport_code, ', ' ORDER BY airport_code) AS airports,
           COUNT(*)                                       AS count
    FROM airports_data
    GROUP BY city ->> 'en', country ->> 'en'
    HAVING COUNT(*) > 1
    ORDER BY count DESC, city, country
    LIMIT 10
    ```

### fix DEMODB_TIMETABLE_B_01

- section: TIMETABLE   tier: Basic
- title: departures in the next 24 hours
- why: Different routes can depart simultaneously; scheduled departure alone does not give a stable order.
- request: Show flights departing SVO from bookings.now(), inclusive, until 24 hours later, exclusive. Show flight, route, arrival airport, local scheduled departure and status, ordered by scheduled departure and flight id.
- sql:

    ```sql
    SELECT flight_id, route_no, arrival_airport, scheduled_departure_local, status
    FROM timetable
    WHERE departure_airport = 'SVO'
      AND scheduled_departure >= bookings.now()
      AND scheduled_departure < bookings.now() + INTERVAL '24 hours'
    ORDER BY scheduled_departure, flight_id
    ```

### add DEMODB_SCHEMA_I_01

- section: SCHEMA   tier: Intermediate
- title: bookings whose totals need reconciliation
- why: Booking amounts and the booking–ticket–segment path are uncovered. Aggregating from bookings also retains bookings without priced segments.
- request: Find bookings whose total amount differs from the sum of their segment prices, treating no segments as zero. Show booking reference, recorded total and segment total, ordered by reference.
- sql:

    ```sql
    SELECT b.book_ref,
           b.total_amount,
           COALESCE(SUM(s.price), 0) AS segment_total
    FROM bookings b
             LEFT JOIN tickets t ON t.book_ref = b.book_ref
             LEFT JOIN segments s ON s.ticket_no = t.ticket_no
    GROUP BY b.book_ref, b.total_amount
    HAVING b.total_amount <> COALESCE(SUM(s.price), 0)
    ORDER BY b.book_ref
    ```

### add DEMODB_SCHEMA_A_01

- section: SCHEMA   tier: Advanced
- title: passengers still awaiting boarding
- why: This covers the composite segment–boarding-pass foreign key and distinguishes a missing pass from a pass with a NULL boarding time.
- request: For flights currently Boarding, list sold segments whose passenger has no recorded boarding time, including segments without a boarding pass. Show flight, ticket, passenger name, seat and boarding number, ordered by flight and ticket.
- sql:

    ```sql
    SELECT f.flight_id,
           s.ticket_no,
           t.passenger_name,
           bp.seat_no,
           bp.boarding_no
    FROM flights f
             JOIN segments s ON s.flight_id = f.flight_id
             JOIN tickets t ON t.ticket_no = s.ticket_no
             LEFT JOIN boarding_passes bp ON bp.ticket_no = s.ticket_no
        AND bp.flight_id = s.flight_id
    WHERE f.status = 'Boarding'
      AND bp.boarding_time IS NULL
    ORDER BY f.flight_id, s.ticket_no
    ```

### add DEMODB_SCHEMA_I_02

- section: SCHEMA   tier: Intermediate
- title: outbound and return tickets in one booking
- why: The unique key on booking, passenger id and outbound flag supports an exact pairing that is not yet exercised.
- request: List passengers who have both outbound and return tickets in the same booking. Show booking reference, booking date, passenger id and both ticket numbers, ordered by booking and passenger id.
- sql:

    ```sql
    SELECT b.book_ref,
           b.book_date,
           o.passenger_id,
           o.ticket_no AS outbound_ticket,
           i.ticket_no AS return_ticket
    FROM bookings b
             JOIN tickets o ON o.book_ref = b.book_ref AND o.outbound
             JOIN tickets i ON i.book_ref = o.book_ref
        AND i.passenger_id = o.passenger_id
        AND NOT i.outbound
    ORDER BY b.book_ref, o.passenger_id
    ```

### add DEMODB_SCHEMA_B_01

- section: SCHEMA   tier: Basic
- title: sold segments affected by cancellation
- why: A simple join and count introduce the uncovered sales data through a practical operational question and populate Basic in SCHEMA.
- request: How many sold segments belong to flights whose status is Cancelled?
- sql:

    ```sql
    SELECT COUNT(*) AS affected_segments
    FROM segments s
             JOIN flights f ON f.flight_id = s.flight_id
    WHERE f.status = 'Cancelled'
    ```

### add DEMODB_ROUTES_I_06

- section: ROUTES   tier: Intermediate
- title: invalid weekday schedules
- why: B_03 relies on seven array entries meaning seven different weekdays; the DDL does not enforce that fact. Guard the assumption once.
- request: Find route periods whose weekday array is empty, contains NULL or values outside 1–7, or repeats a weekday. Show route, validity and weekdays, ordered by route and validity.
- sql:

    ```sql
    SELECT route_no, validity, days_of_week
    FROM routes
    WHERE CARDINALITY(days_of_week) = 0
       OR EXISTS (SELECT 1
                  FROM UNNEST(days_of_week) AS d(day)
                  WHERE day IS NULL OR day NOT BETWEEN 1 AND 7)
       OR CARDINALITY(days_of_week) <>
          (SELECT COUNT(DISTINCT day)
           FROM UNNEST(days_of_week) AS d(day))
    ORDER BY route_no, validity
    ```

### add DEMODB_SEATS_I_04

- section: SEATS   tier: Intermediate
- title: seat numbers that cannot be parsed
- why: I_02 assumes a positive row number followed by one letter, but the DDL permits arbitrary text. A separate check protects its cast without complicating that exercise.
- request: Find seats whose number is not a positive decimal row number followed by one uppercase letter, or whose row number exceeds the integer range used by the parsing exercise. Order by airplane and seat number.
- sql:

    ```sql
    SELECT airplane_code, seat_no
    FROM seats
    WHERE CASE
              WHEN seat_no ~ '^[1-9][0-9]*[A-Z]$'
                  THEN LEFT(seat_no, -1)::numeric > 2147483647
              ELSE TRUE
          END
    ORDER BY airplane_code, seat_no
    ```

### add DEMODB_AIRPORTS_DATA_I_04

- section: AIRPORTS_DATA   tier: Intermediate
- title: missing English airport labels
- why: English grouping and filtering assume usable translations, while NOT NULL applies only to the JSON documents. Check that assumption separately.
- request: Find airports whose English airport name, city or country is missing, is not a JSON string, or is blank. Show the code and the three English values, ordered by code.
- sql:

    ```sql
    SELECT airport_code,
           airport_name ->> 'en' AS airport_name,
           city ->> 'en'         AS city,
           country ->> 'en'      AS country
    FROM airports_data
    WHERE JSONB_TYPEOF(airport_name -> 'en') IS DISTINCT FROM 'string'
       OR JSONB_TYPEOF(city -> 'en') IS DISTINCT FROM 'string'
       OR JSONB_TYPEOF(country -> 'en') IS DISTINCT FROM 'string'
       OR BTRIM(airport_name ->> 'en') = ''
       OR BTRIM(city ->> 'en') = ''
       OR BTRIM(country ->> 'en') = ''
    ORDER BY airport_code
    ```

### remove DEMODB_AIRPLANES_I_02

- section: AIRPLANES   tier: Intermediate
- title: whether the view agrees with the table
- why: The published view defines its model using exactly the expression being compared, so the query cannot reveal a discrepancy under this DDL. AIRPLANES_I_01 keeps Intermediate populated.