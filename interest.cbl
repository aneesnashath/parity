       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTEREST.
      *****************************************************************
      * DAILY INTEREST ACCRUAL - LEGACY BATCH PROGRAM
      *
      * READS  : input.dat   (24-BYTE FIXED WIDTH RECORDS)
      * WRITES : output.dat  (ACCOUNT, INTEREST, NEW BALANCE)
      *
      * MONETARY FIELDS USE PIC S9(7)V99 COMP-3 (PACKED DECIMAL).
      * ALL ARITHMETIC IS EXACT BASE-10. THE ROUNDED PHRASE USES
      * COBOL DEFAULT SEMANTICS: NEAREST-AWAY-FROM-ZERO (HALF-UP).
      *****************************************************************

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT IN-FILE  ASSIGN TO "input.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT OUT-FILE ASSIGN TO "output.dat"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.

       FD  IN-FILE.
       01  IN-REC.
           05  IN-ACCT        PIC X(10).
           05  IN-PRINCIPAL   PIC 9(7)V99.
           05  IN-RATE        PIC 9(2)V999.

       FD  OUT-FILE.
       01  OUT-REC.
           05  OUT-ACCT       PIC X(10).
           05  FILLER         PIC X.
           05  OUT-INTEREST   PIC ----------9.99.
           05  FILLER         PIC X.
           05  OUT-TOTAL      PIC ----------9.99.

       WORKING-STORAGE SECTION.
       01  WS-EOF             PIC X          VALUE "N".
       01  WS-PRINCIPAL       PIC S9(7)V99   COMP-3.
       01  WS-RATE            PIC S9(2)V999  COMP-3.
       01  WS-INTEREST        PIC S9(7)V99   COMP-3.
       01  WS-TOTAL           PIC S9(7)V99   COMP-3.

       PROCEDURE DIVISION.

       MAIN-PARA.
           OPEN INPUT  IN-FILE
           OPEN OUTPUT OUT-FILE
           PERFORM UNTIL WS-EOF = "Y"
               READ IN-FILE
                   AT END
                       MOVE "Y" TO WS-EOF
                   NOT AT END
                       PERFORM PROCESS-REC
               END-READ
           END-PERFORM
           CLOSE IN-FILE
           CLOSE OUT-FILE
           STOP RUN.

       PROCESS-REC.
           MOVE SPACES TO OUT-REC
           MOVE IN-PRINCIPAL TO WS-PRINCIPAL
           MOVE IN-RATE      TO WS-RATE
           COMPUTE WS-INTEREST ROUNDED =
               (WS-PRINCIPAL * WS-RATE) / 100
           ADD WS-PRINCIPAL TO WS-INTEREST GIVING WS-TOTAL
           MOVE IN-ACCT      TO OUT-ACCT
           MOVE WS-INTEREST  TO OUT-INTEREST
           MOVE WS-TOTAL     TO OUT-TOTAL
           WRITE OUT-REC
           END-WRITE.
