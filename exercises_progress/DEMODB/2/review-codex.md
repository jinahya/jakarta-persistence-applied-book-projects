### fix DEMODB_FLIGHTS_A_03
- section: FLIGHTS   tier: Advanced
- title: The five fullest flights of the first day
- why: A boarding pass can belong to someone who did not board. Count non-NULL boarding numbers, retain flights with no passes, and rank by the unrounded share.
- request: For arrived flights scheduled on 2025-10-01, show the five with the highest share of seats boarded, breaking ties by flight id. Show the flight, route, airplane, boarded passengers, seats and percentage to one decimal.
- sql:

    ```sql
    SELECT f.flight_id,
           f.route_no,
           r.airplane_code,
           COUNT(bp.boarding_no)                                  AS boarded,
           s.seats,
           ROUND(100.0 * COUNT(bp.boarding_no) / s.seats, 1)       AS boarded_pct
    FROM flights f
             JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure
             JOIN (SELECT airplane_code, COUNT(*) AS seats FROM seats GROUP BY airplane_code) s
                  ON s.airplane_code = r.airplane_code
             LEFT JOIN boarding_passes bp ON bp.flight_id = f.flight_id
    WHERE f.status = 'Arrived'
      AND f.scheduled_departure >= '2025-10-01'
      AND f.scheduled_departure < '2025-10-02'
    GROUP BY f.flight_id, f.route_no, r.airplane_code, s.seats
    ORDER BY 100.0 * COUNT(bp.boarding_no) / s.seats DESC, f.flight_id
    LIMIT 5
    ```

### fix DEMODB_SCHEMA_I_02
- section: SCHEMA   tier: Intermediate
- title: The ten airports with the most passengers boarded in the first week
- why: Counting every boarding pass includes passengers who checked in but did not board.
- request: For flights scheduled from 2025-10-01 through 2025-10-07, show the ten departure airports with the most boarded passengers. Show code, name and count, ordered by count descending and then code.
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

### fix DEMODB_BOOKINGS_A_01
- section: BOOKINGS   tier: Advanced
- title: How many bookings do not add up
- why: Inner joins hide bookings with no tickets or no priced segments, including positive totals that should fail this audit.
- request: Count bookings whose total amount differs from the sum of their tickets' segment prices, treating an empty sum as zero.
- sql:

    ```sql
    SELECT COUNT(*) AS bookings
    FROM (SELECT b.book_ref
          FROM bookings b
                   LEFT JOIN tickets t ON t.book_ref = b.book_ref
                   LEFT JOIN segments s ON s.ticket_no = t.ticket_no
          GROUP BY b.book_ref, b.total_amount
          HAVING b.total_amount <> COALESCE(SUM(s.price), 0)) x
    ```

### fix DEMODB_SCHEMA_B_03
- section: SCHEMA   tier: Basic
- title: The foreign keys, and what they reference
- why: A `regclass` sorts by its underlying object identifier, rather than the displayed table name. Cast it to text to satisfy the requested alphabetical order.
- request: List the foreign keys of the bookings schema, showing table name, constraint name and definition, ordered by table name and then constraint name.
- sql:

    ```sql
    SELECT conrelid::regclass::text AS table_name,
           conname,
           PG_GET_CONSTRAINTDEF(oid) AS definition
    FROM pg_constraint
    WHERE connamespace = 'bookings'::regnamespace
      AND contype = 'f'
    ORDER BY table_name, conname
    ```

### fix DEMODB_BOOKINGS_B_01
- section: BOOKINGS   tier: Basic
- title: The bookings of the first minute
- why: Booking timestamps are not unique. Add the primary key to make the order stable.
- request: Find bookings made from 2025-09-01 00:00 up to but not including 00:01. Show whole rows, ordered by booking date and then booking reference.
- sql:

    ```sql
    SELECT *
    FROM bookings
    WHERE book_date >= '2025-09-01 00:00'
      AND book_date < '2025-09-01 00:01'
    ORDER BY book_date, book_ref
    ```

### fix DEMODB_SCHEMA_I_05
- section: SCHEMA   tier: Intermediate
- title: Passengers and seats on upcoming flights from Sheremetyevo
- why: The request references an exercise absent from this unit, and departure time alone does not give a stable order.
- request: For flights from SVO scheduled in the next 24 hours from bookings.now(), show flight id, destination, local departure, airplane, booked passengers and seats. Include flights with no bookings, ordered by scheduled departure and then flight id.
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
    GROUP BY t.flight_id, t.arrival_airport, t.scheduled_departure,
             t.scheduled_departure_local, t.airplane_code
    ORDER BY t.scheduled_departure, t.flight_id
    ```

### fix DEMODB_SCHEMA_A_03
- section: SCHEMA   tier: Advanced
- title: Airports one and two routes away from Sheremetyevo
- why: The answer includes a zero-flight row that the request does not ask for. Clarify that this explores published route versions, rather than promising connections on a particular date.
- request: Across all published route versions, count distinct airports reachable from SVO using exactly one route and exactly two routes. An airport may count at both lengths, and a two-route return to SVO counts.
- sql:

    ```sql
    WITH RECURSIVE hops AS (SELECT 'SVO'::bpchar AS airport, 0 AS flights
                           UNION
                           SELECT r.arrival_airport, h.flights + 1
                           FROM hops h
                                    JOIN routes r ON r.departure_airport = h.airport
                           WHERE h.flights < 2)
    SELECT flights, COUNT(*) AS airports
    FROM hops
    WHERE flights > 0
    GROUP BY flights
    ORDER BY flights
    ```

### add DEMODB_SCHEMA_I_06
- section: SCHEMA   tier: Intermediate
- title: Flights with no applicable route version
- why: The DDL prevents overlapping versions of a route but does not require a flight to match any version. This check guards the temporal joins used throughout the unit.
- request: List flights with no route version valid at their scheduled departure, ordered by departure and then flight id.
- sql:

    ```sql
    SELECT f.flight_id, f.route_no, f.scheduled_departure
    FROM flights f
    WHERE NOT EXISTS (SELECT 1
                      FROM routes r
                      WHERE r.route_no = f.route_no
                        AND r.validity @> f.scheduled_departure)
    ORDER BY f.scheduled_departure, f.flight_id
    ```

### add DEMODB_SEGMENTS_I_05
- section: SEGMENTS   tier: Intermediate
- title: Flights with a zero Economy denominator
- why: The price constraint permits zero, so the Business-to-Economy ratio can divide by zero. Guard the positive-denominator assumption with a check rather than changing every ratio exercise.
- request: List flights sold in both Economy and Business whose cheapest Economy price is zero, ordered by flight id.
- sql:

    ```sql
    SELECT flight_id,
           MIN(price) FILTER (WHERE fare_conditions = 'Economy') AS economy
    FROM segments
    GROUP BY flight_id
    HAVING MIN(price) FILTER (WHERE fare_conditions = 'Economy') = 0
       AND COUNT(*) FILTER (WHERE fare_conditions = 'Business') > 0
    ORDER BY flight_id
    ```

### add DEMODB_SCHEMA_A_05
- section: SCHEMA   tier: Advanced
- title: Tickets whose segments do not form a connection
- why: The itinerary and layover exercises assume distinct departure times and continuous journeys. Neither property is enforced; this check guards both assumptions.
- request: Find ticket segments with simultaneous scheduled departures, a departure airport different from the previous arrival airport, or a departure before the previous arrival. Show the ticket, flight and relevant previous-leg details.
- sql:

    ```sql
    SELECT ticket_no, flight_id, departure_airport, scheduled_departure,
           previous_airport, previous_arrival, simultaneous
    FROM (SELECT s.ticket_no,
                 f.flight_id,
                 r.departure_airport,
                 f.scheduled_departure,
                 LAG(r.arrival_airport) OVER w AS previous_airport,
                 LAG(f.scheduled_arrival) OVER w AS previous_arrival,
                 COUNT(*) OVER (PARTITION BY s.ticket_no, f.scheduled_departure) AS simultaneous
          FROM segments s
                   JOIN flights f ON f.flight_id = s.flight_id
                   JOIN routes r ON r.route_no = f.route_no AND r.validity @> f.scheduled_departure
          WINDOW w AS (PARTITION BY s.ticket_no ORDER BY f.scheduled_departure, f.flight_id)) x
    WHERE simultaneous > 1
       OR departure_airport <> previous_airport
       OR scheduled_departure < previous_arrival
    ORDER BY ticket_no, scheduled_departure, flight_id
    ```

### add DEMODB_TICKETS_I_05
- section: TICKETS   tier: Intermediate
- title: Passenger ids recorded under different names
- why: The passenger ranking groups by both id and name while asking for counts by id. Check the assumed name consistency rather than choosing an arbitrary name in that exercise.
- request: List passenger ids recorded with more than one distinct passenger name, showing the number of names, ordered by passenger id.
- sql:

    ```sql
    SELECT passenger_id, COUNT(DISTINCT passenger_name) AS names
    FROM tickets
    GROUP BY passenger_id
    HAVING COUNT(DISTINCT passenger_name) > 1
    ORDER BY passenger_id
    ```

### add DEMODB_SCHEMA_I_07
- section: SCHEMA   tier: Intermediate
- title: Seat capacity and cabin mix by airplane model
- why: The unit uses seat totals but never presents the cabin mix alongside the model's range and speed. This covers useful airplane columns and preserves models without seats.
- request: Show every airplane model's code, name, range, cruise speed, total seats and seats in each travel class, ordered by code.
- sql:

    ```sql
    SELECT a.airplane_code,
           a.model,
           a.range,
           a.speed,
           COUNT(s.seat_no) AS seats,
           COUNT(s.seat_no) FILTER (WHERE s.fare_conditions = 'Economy') AS economy,
           COUNT(s.seat_no) FILTER (WHERE s.fare_conditions = 'Comfort') AS comfort,
           COUNT(s.seat_no) FILTER (WHERE s.fare_conditions = 'Business') AS business
    FROM airplanes a
             LEFT JOIN seats s ON s.airplane_code = a.airplane_code
    GROUP BY a.airplane_code, a.model, a.range, a.speed
    ORDER BY a.airplane_code
    ```

### add DEMODB_SCHEMA_I_08
- section: SCHEMA   tier: Intermediate
- title: Today's departures in each airport's local time
- why: Existing date filters use the session time zone. This exercises the timetable's local timestamps and the airport time zones for a practical departure-board question.
- request: Show flights departing today according to their departure airport's local date at bookings.now(). Include airport code, name, time zone, flight, destination and local departure, ordered by airport, local departure and flight id.
- sql:

    ```sql
    SELECT a.airport_code,
           a.airport_name,
           a.timezone,
           t.flight_id,
           t.arrival_airport,
           t.scheduled_departure_local
    FROM timetable t
             JOIN airports a ON a.airport_code = t.departure_airport
    WHERE t.scheduled_departure_local::date =
          (bookings.now() AT TIME ZONE a.timezone)::date
    ORDER BY a.airport_code, t.scheduled_departure_local, t.flight_id
    ```

### add DEMODB_SCHEMA_I_09
- section: SCHEMA   tier: Intermediate
- title: Current Monday services from Sheremetyevo
- why: Route validity, operating-day arrays, local departure times and estimated duration are otherwise only incidental to the exercises. Together they answer a useful schedule question.
- request: Among route versions valid at bookings.now(), list services from SVO whose operating-day array contains Monday (1). Show route, destination code and name, local departure time, duration and airplane model, ordered by departure time and route.
- sql:

    ```sql
    SELECT r.route_no,
           r.arrival_airport,
           a.airport_name,
           r.scheduled_time,
           r.duration,
           p.model
    FROM routes r
             JOIN airports a ON a.airport_code = r.arrival_airport
             JOIN airplanes p ON p.airplane_code = r.airplane_code
    WHERE r.departure_airport = 'SVO'
      AND r.validity @> bookings.now()
      AND 1 = ANY (r.days_of_week)
    ORDER BY r.scheduled_time, r.route_no
    ```