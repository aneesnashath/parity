import java.io.*;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/**
 * Java translation of interest.cbl — Daily Interest Accrual batch program.
 *
 * Input  (input.dat):  24-byte fixed-width records, one per line
 *   Offset  0-9  : account (PIC X(10))
 *   Offset 10-18 : principal digits PIC 9(7)V99  — 9 ASCII digits, implied V after position 7
 *   Offset 19-23 : rate digits      PIC 9(2)V999 — 5 ASCII digits, implied V after position 2
 *
 * Output (output.dat): 40-byte formatted records
 *   account (10) + ' ' + interest (14) + ' ' + total (14)
 *
 * Arithmetic:
 *   interest = ROUND_HALF_UP( (principal * rate) / 100, 2 )
 *   total    = principal + interest
 *   Both stored as PIC S9(7)V99 COMP-3: integer-cent value is truncated modulo 10^9
 *   before formatting (mimics COBOL packed-decimal overflow behaviour).
 *
 * Formatting — PIC ----------9.99 (14 chars):
 *   Right-justified, space-padded, always includes decimal point and two fractional digits.
 */
public class InterestAccrual {

    // PIC S9(7)V99 COMP-3 stores at most 9 decimal digits: 7 integer + 2 fractional.
    // Overflow wraps the integer-cent representation modulo 10^9.
    static final long CENTS_MODULUS = 1_000_000_000L;   // 10^9

    static final int FIELD_WIDTH = 14;   // width of PIC ----------9.99

    public static void main(String[] args) throws IOException {
        String inputPath  = "input.dat";
        String outputPath = "java_output.dat";

        try (BufferedReader reader = new BufferedReader(
                 new InputStreamReader(new FileInputStream(inputPath), StandardCharsets.US_ASCII));
             BufferedWriter writer = new BufferedWriter(
                 new OutputStreamWriter(new FileOutputStream(outputPath), StandardCharsets.US_ASCII))) {

            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty()) continue;
                String outLine = processRecord(line);
                writer.write(outLine);
                writer.newLine();
            }
        }
    }

    /**
     * Processes one 24-character input record and returns the 40-character output line.
     */
    static String processRecord(String record) {
        // --- parse input ---
        String account   = record.substring(0, 10);
        String pRaw      = record.substring(10, 19);   // 9 digits, PIC 9(7)V99
        String rRaw      = record.substring(19, 24);   // 5 digits, PIC 9(2)V999

        // Convert implied-decimal strings to BigDecimal
        // PIC 9(7)V99  : value = digits / 100
        // PIC 9(2)V999 : value = digits / 1000
        BigDecimal principal = new BigDecimal(pRaw).movePointLeft(2);
        BigDecimal rate      = new BigDecimal(rRaw).movePointLeft(3);

        // --- compute interest (COBOL ROUNDED = HALF_UP) ---
        BigDecimal interest = principal.multiply(rate)
                                       .divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);

        // --- add to get total ---
        BigDecimal total = principal.add(interest);

        // --- apply COBOL PIC S9(7)V99 COMP-3 overflow truncation ---
        interest = truncateToPic9_7V99(interest);
        total    = truncateToPic9_7V99(total);

        // --- format output ---
        return account
             + ' '
             + formatPicture(interest)
             + ' '
             + formatPicture(total);
    }

    /**
     * Simulates COBOL PIC S9(7)V99 COMP-3 storage:
     * the value in integer-cents is kept modulo 10^9, sign preserved.
     */
    static BigDecimal truncateToPic9_7V99(BigDecimal value) {
        // Convert to integer cents, truncate, convert back
        long cents = value.multiply(BigDecimal.valueOf(100))
                          .setScale(0, RoundingMode.HALF_UP)
                          .longValueExact();
        // Truncate to 9 decimal digits of the absolute integer
        boolean negative = cents < 0;
        long absCents = Math.abs(cents) % CENTS_MODULUS;
        long truncated = negative ? -absCents : absCents;
        return BigDecimal.valueOf(truncated, 2);   // scale=2 -> divide by 100
    }

    /**
     * Formats a value using COBOL PIC ----------9.99 semantics:
     * right-justified in a 14-character field, space-padded on the left,
     * always shows two decimal digits and a decimal point.
     * Negative values would show a leading '-', but since principal and rate
     * are always non-negative after truncation the sign is not exercised here.
     */
    static String formatPicture(BigDecimal value) {
        // Format with exactly 2 decimal places
        String formatted = value.abs().setScale(2).toPlainString();
        if (value.signum() < 0) {
            formatted = "-" + formatted;
        }
        // Right-pad to FIELD_WIDTH with leading spaces
        return String.format("%" + FIELD_WIDTH + "s", formatted);
    }
}
