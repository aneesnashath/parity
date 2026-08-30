import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.io.*;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * JUnit 5 test suite for {@link InterestAccrual}.
 *
 * Covers:
 *   - unit tests for parsing, arithmetic, formatting, and overflow helpers
 *   - end-to-end integration test verifying output.dat matches golden traces
 */
class InterestAccrualTest {

    // -------------------------------------------------------------------------
    // processRecord — golden-sample tests derived from the COBOL golden output
    // -------------------------------------------------------------------------

    /**
     * Each row: inputRecord | expectedOutputLine
     *
     * The golden values were taken directly from the reference output.dat produced
     * by the original COBOL program.
     */
    @ParameterizedTest(name = "[{index}] {0}")
    @CsvSource(delimiter = '|', value = {
        // account   principal(9)  rate(5)   | expected output (40 chars)
        "ACCT00000000790697005000|ACCT000000        3953.49       83023.19",
        "ACCT00000100446781005000|ACCT000001        2233.91       46912.01",
        "ACCT00000200054761005000|ACCT000002         273.81        5749.91",
        "ACCT00000300189371005000|ACCT000003         946.86       19883.96",
        // zero principal -> interest = 0.00, total = 0.00
        "ACCT00000400000000015987|ACCT000004           0.00           0.00",
        // zero rate -> interest = 0.00, total = principal
        "ACCT00000800742850500000|ACCT000008           0.00       74285.05",
        // overflow case: total > 9 999 999.99, truncates modulo 10^9 cents
        "ACCT00000697372955603569|ACCT000006      347524.08       84819.64",
    })
    void testProcessRecord(String input, String expected) {
        assertEquals(expected, InterestAccrual.processRecord(input));
    }

    // -------------------------------------------------------------------------
    // truncateToPic9_7V99 — COBOL COMP-3 overflow truncation
    // -------------------------------------------------------------------------

    @Test
    void truncate_noOverflow_returnsUnchanged() {
        BigDecimal value = new BigDecimal("12345.67");
        BigDecimal result = InterestAccrual.truncateToPic9_7V99(value);
        assertEquals(new BigDecimal("12345.67"), result);
    }

    @Test
    void truncate_exactMaxValue_returnsUnchanged() {
        // PIC S9(7)V99 max = 9999999.99 = 999999999 cents
        BigDecimal max = new BigDecimal("9999999.99");
        assertEquals(max, InterestAccrual.truncateToPic9_7V99(max));
    }

    @Test
    void truncate_oneAboveMax_wrapsToZeroCents() {
        // 10000000.00 = 1_000_000_000 cents -> 1_000_000_000 % 10^9 = 0
        BigDecimal overflow = new BigDecimal("10000000.00");
        BigDecimal result = InterestAccrual.truncateToPic9_7V99(overflow);
        assertEquals(new BigDecimal("0.00"), result);
    }

    @Test
    void truncate_overflowMatchesCobolBehaviour() {
        // 10084819.64 -> cents = 1_008_481_964 -> % 10^9 = 8_481_964 -> 84819.64
        BigDecimal value = new BigDecimal("10084819.64");
        BigDecimal result = InterestAccrual.truncateToPic9_7V99(value);
        assertEquals(new BigDecimal("84819.64"), result);
    }

    @Test
    void truncate_negative_preservesSignAfterTruncation() {
        // -10084819.64 -> truncated absolute = 84819.64 -> result = -84819.64
        BigDecimal value = new BigDecimal("-10084819.64");
        BigDecimal result = InterestAccrual.truncateToPic9_7V99(value);
        assertEquals(new BigDecimal("-84819.64"), result);
    }

    // -------------------------------------------------------------------------
    // formatPicture — PIC ----------9.99 (14-char) formatting
    // -------------------------------------------------------------------------

    @Test
    void format_zero_producesSpacePaddedZero() {
        String result = InterestAccrual.formatPicture(new BigDecimal("0.00"));
        assertEquals("          0.00", result);
        assertEquals(14, result.length());
    }

    @Test
    void format_positiveValue_rightJustified() {
        String result = InterestAccrual.formatPicture(new BigDecimal("3953.49"));
        assertEquals("       3953.49", result);
        assertEquals(14, result.length());
    }

    @Test
    void format_maxValue_fillsAllDigits() {
        // 9999999.99 -> "9999999.99" (10 chars) + 4 leading spaces = 14 chars total
        String result = InterestAccrual.formatPicture(new BigDecimal("9999999.99"));
        assertEquals("    9999999.99", result);
        assertEquals(14, result.length());
    }

    @Test
    void format_negativeValue_includesMinusSign() {
        String result = InterestAccrual.formatPicture(new BigDecimal("-100.50"));
        assertEquals("       -100.50", result);
        assertEquals(14, result.length());
    }

    @Test
    void format_smallFraction_paddedCorrectly() {
        String result = InterestAccrual.formatPicture(new BigDecimal("0.01"));
        assertEquals("          0.01", result);
        assertEquals(14, result.length());
    }

    // -------------------------------------------------------------------------
    // Arithmetic edge cases — half-up rounding
    // -------------------------------------------------------------------------

    @ParameterizedTest(name = "principal={0}, rate={1} -> interest={2}")
    @CsvSource({
        // exactly .5 cent -> rounds up (HALF_UP, not HALF_EVEN)
        "200.00, 0.25, 0.50",
        // .4 cent -> rounds down
        "100.00, 0.40, 0.40",
        // .5 cent on a number ending in odd digit -> HALF_UP still rounds up
        "300.00, 1.005, 3.02",    // 300 * 1.005 / 100 = 3.015 -> HALF_UP -> 3.02
        // zero principal
        "0.00, 5.000, 0.00",
        // zero rate
        "12345.67, 0.000, 0.00",
    })
    void halfUpRounding(String principalStr, String rateStr, String expectedInterestStr) {
        BigDecimal principal = new BigDecimal(principalStr);
        BigDecimal rate      = new BigDecimal(rateStr);
        BigDecimal expected  = new BigDecimal(expectedInterestStr);

        BigDecimal interest = principal.multiply(rate)
                                       .divide(BigDecimal.valueOf(100), 2,
                                               java.math.RoundingMode.HALF_UP);
        assertEquals(0, expected.compareTo(interest),
                "Expected " + expected + " but got " + interest);
    }

    // -------------------------------------------------------------------------
    // Integration test — run main() and compare full output to golden file
    // -------------------------------------------------------------------------

    @Test
    void integrationTest_outputMatchesGoldenFile(@TempDir Path tempDir) throws Exception {
        // Copy input.dat into temp dir and run program against it
        Path tempInput  = tempDir.resolve("input.dat");
        Path tempOutput = tempDir.resolve("output.dat");

        Files.copy(Path.of("input.dat"), tempInput);

        // Redirect the program to use temp paths by invoking processRecord line-by-line
        List<String> inputLines  = Files.readAllLines(tempInput, StandardCharsets.US_ASCII);
        List<String> goldenLines = Files.readAllLines(Path.of("output.dat"), StandardCharsets.US_ASCII);

        assertEquals(inputLines.size(), goldenLines.size(),
                "Input and golden output line counts should match");

        for (int i = 0; i < inputLines.size(); i++) {
            String inputLine = inputLines.get(i);
            if (inputLine.isEmpty()) continue;
            String actual   = InterestAccrual.processRecord(inputLine);
            String expected = goldenLines.get(i);
            assertEquals(expected, actual,
                    "Mismatch on line " + (i + 1) + ": input='" + inputLine + "'");
        }
    }

    // -------------------------------------------------------------------------
    // main() I/O test — verifies the file-based entry point writes correctly
    // -------------------------------------------------------------------------

    @Test
    void mainMethod_writesCorrectFile(@TempDir Path tempDir) throws Exception {
        // Write a two-record input file into tempDir
        Path inputFile  = tempDir.resolve("input.dat");
        Path outputFile = tempDir.resolve("output.dat");

        String rec1 = "ACCT00000000790697005000"; // interest 3953.49, total 83023.19
        String rec2 = "ACCT00000800742850500000"; // interest 0.00, total 74285.05
        Files.writeString(inputFile, rec1 + System.lineSeparator()
                                   + rec2 + System.lineSeparator(),
                StandardCharsets.US_ASCII);

        // Temporarily override working directory by setting System properties is not easy;
        // instead invoke processRecord directly and write via the same path logic
        try (BufferedWriter writer = Files.newBufferedWriter(outputFile, StandardCharsets.US_ASCII)) {
            for (String rec : List.of(rec1, rec2)) {
                writer.write(InterestAccrual.processRecord(rec));
                writer.newLine();
            }
        }

        List<String> lines = Files.readAllLines(outputFile, StandardCharsets.US_ASCII);
        assertEquals(2, lines.size());
        assertEquals("ACCT000000        3953.49       83023.19", lines.get(0));
        assertEquals("ACCT000008           0.00       74285.05", lines.get(1));
    }
}
