// Display-only constants lifted verbatim from tutor_app.html. The backend is
// the source of truth for question generation; the UI uses these for titles,
// focus text, lexile/day labels, answer colors, and the explain prompts.

export const MATH_WEEKS = {
  1: { title: "Number & Operations", focus: "Decimals: division into decimals, decimal addition & subtraction. Multi-step word problems hiding the operation.", level: "decimals" },
  2: { title: "Number & Operations II", focus: "Decimal multiplication & division mastery. Place value with decimals. Two-operation word problems.", level: "decimals" },
  3: { title: "Fractions, Decimals & %", focus: "Converting between fractions, decimals, percentages. Fraction addition & subtraction.", level: "fractions" },
  4: { title: "Fractions II", focus: "Fraction multiplication & division. Mixed numbers. Word problems combining fractions and decimals.", level: "fractions" },
  5: { title: "Ratios & Proportions", focus: "Ratios, proportions, unit rates. The heaviest 6th-grade concept — depends on fraction/decimal mastery.", level: "ratios" },
  6: { title: "Operations & Algebraic Thinking", focus: "Order of operations (PEMDAS), properties, writing basic expressions. Her 'Low' MAP area.", level: "algebra" },
  7: { title: "Geometry, Area & Volume", focus: "Coordinate planes, area of complex shapes, intro to volume.", level: "geometry" },
  8: { title: "Data & Diagnostic", focus: "Mean, median, mode, range. Comprehensive review and readiness test.", level: "data" },
}

export const ENGLISH_WEEKS = {
  1: { title: "Foundation & Mechanics", focus: "Prefix/suffix decoding, context clues, pronoun rules, dialogue punctuation.", lexile: "515-550" },
  2: { title: "Mechanics II", focus: "Sentence-level mechanics, capitalization, periods, punctuation execution. Catching rushing errors.", lexile: "550-580" },
  3: { title: "Root Words & Sentence Combining", focus: "Greek & Latin roots. Combining simple sentences into complex ones using conjunctions.", lexile: "580-620" },
  4: { title: "Roots II & Complex Sentences", focus: "More roots, eliminating choppy writing, informational text comprehension.", lexile: "620-660" },
  5: { title: "Advanced Editing & Paragraphs", focus: "Tier-2 academic words, outlining, writing one flawless paragraph at a time.", lexile: "660-700" },
  6: { title: "Paragraph Structure II", focus: "Multi-paragraph structure, main idea, supporting detail across subjects.", lexile: "700-730" },
  7: { title: "6th Grade Readiness Stamina", focus: "Speed drills on roots/prefixes. Reading science/history articles, highlighting main ideas.", lexile: "730-760" },
  8: { title: "Readiness Stamina II", focus: "Heavy proofreading challenges — she edits highly flawed texts. Stretch toward 780L.", lexile: "760-780" },
}

export const LEXILE_BY_WEEK = { 1: 540, 2: 570, 3: 600, 4: 640, 5: 680, 6: 715, 7: 745, 8: 780 }

export function passageLines(week, day) {
  const weekFloor = { 1: 5, 2: 8, 3: 10, 4: 12, 5: 14, 6: 16, 7: 18, 8: 20 }
  const floor = weekFloor[week] || 5
  return Math.min(floor + (day - 1) * 2, floor + 12)
}

export const MODES = {
  practice: { label: "Practice", count: 12, icon: "🌱", desc: "daily practice" },
  test: { label: "Weekly Test", count: 15, icon: "🏆", desc: "once a week" },
}

export function practiceCount(day) {
  return Math.min(10 + Math.round((day - 1) * 0.83), 15)
}

export const ANSWER_COLORS = [
  { bg: "linear-gradient(160deg,#3b82f6,#1d4ed8)", solid: "#2563eb" },
  { bg: "linear-gradient(160deg,#14b8a6,#0d9488)", solid: "#0d9488" },
  { bg: "linear-gradient(160deg,#f59e0b,#d97706)", solid: "#ea8a0c" },
  { bg: "linear-gradient(160deg,#ec4899,#be185d)", solid: "#db2777" },
]

export const EXPLAIN_PROMPTS = [
  "Nice! Quick — how did you figure that out?",
  "Got it right! Tell me your thinking in one line.",
  "Yes! What was the first step you did?",
  "Correct! Which operation did you use, and why?",
]
