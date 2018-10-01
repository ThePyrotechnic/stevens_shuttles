CREATE TABLE "Shuttle" (
	"id" int NOT NULL,
  CONSTRAINT Shuttle_pk PRIMARY KEY ("id")
);

CREATE TABLE "Route" (
	"id" int NOT NULL,
	"long_name" TEXT NOT NULL,
	"short_name" TEXT NOT NULL,
	"bounds" int,
  CONSTRAINT Route_pk PRIMARY KEY ("id")
);

CREATE TABLE "Bounds" (
  "id" SERIAL NOT NULL,
	"bounds" box,
	CONSTRAINT Bounds_pk PRIMARY KEY ("id")
);

CREATE TABLE "Stop" (
	"id" int NOT NULL,
	"route_id" int NOT NULL,
  "position" point NOT NULL,
	CONSTRAINT Stop_pk PRIMARY KEY ("id")
);

CREATE TABLE "ConfirmedStop" (
	"id" serial NOT NULL,
	"shuttle" int NOT NULL,
	"route" int NOT NULL,
	"stop" int NOT NULL,
	"arrival_time" timestamp with time zone NOT NULL,
	"expected_time" timestamp with time zone,
	CONSTRAINT ConfirmedStop_pk PRIMARY KEY ("id")
);


ALTER TABLE "Route" ADD CONSTRAINT "Route_fk0" FOREIGN KEY ("bounds") REFERENCES "Bounds"("id");

ALTER TABLE "Stop" ADD CONSTRAINT "Stop_fk0" FOREIGN KEY ("route_id") REFERENCES "Route"("id");

ALTER TABLE "ConfirmedStop" ADD CONSTRAINT "ConfirmedStop_fk0" FOREIGN KEY ("shuttle") REFERENCES "Shuttle"("id");
ALTER TABLE "ConfirmedStop" ADD CONSTRAINT "ConfirmedStop_fk1" FOREIGN KEY ("route") REFERENCES "Route"("id");
ALTER TABLE "ConfirmedStop" ADD CONSTRAINT "ConfirmedStop_fk2" FOREIGN KEY ("stop") REFERENCES "Stop"("id");
