import { safeImageUrl } from "@/lib/url";
import type { Recall } from "@/types/api";

export interface RecallImageSelection {
  src: string;
  label: string;
  isFallback: boolean;
}

const FALLBACKS = {
  fish: "/images/recall-fallback/fish.jpg",
  meat: "/images/recall-fallback/meat.jpg",
  dairy: "/images/recall-fallback/dairy-eggs.jpg",
  produce: "/images/recall-fallback/produce.jpg",
  bakery: "/images/recall-fallback/bakery-cereals.jpg",
  prepared: "/images/recall-fallback/prepared-packaged.jpg",
  supplements: "/images/recall-fallback/supplements-baby.jpg",
  beverages: "/images/recall-fallback/beverages.jpg",
  feed: "/images/recall-fallback/feed.jpg",
  generic: "/images/recall-fallback/generic-food.jpg",
} as const;

type FallbackKey = keyof typeof FALLBACKS;

const MATCHERS: Array<{ key: FallbackKey; terms: string[]; label: string }> = [
  {
    key: "fish",
    terms: ["fish", "pesce", "ittic", "tonno", "salmone", "merluzz", "sgombro", "mackerel", "swordfish", "mollusc", "mollusch", "cozze", "vongol", "gamber", "calamar", "polpo"],
    label: "ittico",
  },
  {
    key: "feed",
    terms: ["feed materials", "animal feed", "mangime", "foraggio"],
    label: "mangimi",
  },
  {
    key: "meat",
    terms: ["meat", "carne", "poultry", "pollo", "chicken", "tacchino", "turkey", "beef", "manzo", "pork", "maiale", "speck", "prosciutto", "salame", "salsic", "hamburger"],
    label: "carne e pollame",
  },
  {
    key: "dairy",
    terms: ["dairy", "latte", "milk", "cheese", "formagg", "brie", "robiola", "caciotta", "formaggella", "duble", "yogurt", "burro", "butter", "uova", "egg"],
    label: "latticini e uova",
  },
  {
    key: "produce",
    terms: ["fruits", "fruit", "vegetable", "verdura", "frutta", "insalata", "salad", "broccoli", "pomodoro", "tomato", "carota", "apple", "mela", "pesto"],
    label: "frutta e verdura",
  },
  {
    key: "bakery",
    terms: ["cereal", "bakery", "bread", "pane", "biscott", "amarett", "pasta", "riso", "rice", "farina", "wheat", "grano"],
    label: "cereali e panetteria",
  },
  {
    key: "prepared",
    terms: ["prepared", "snack", "confezion", "packaged", "meal", "piatto", "salsa", "sauce", "conserv", "jar", "vasetto", "scatola", "box"],
    label: "piatti e confezionati",
  },
  {
    key: "supplements",
    terms: ["supplement", "integrator", "vitamin", "epimedyum", "honey", "baby", "gravidanza", "concepimento", "stamina"],
    label: "integratori e alimenti per l'infanzia",
  },
  {
    key: "beverages",
    terms: ["beverage", "drink", "bevanda", "champagne", "vino", "wine", "alcool", "birra", "beer", "acqua", "water", "succo", "juice"],
    label: "bevande",
  },
];

function normalizedRecallText(recall: Pick<Recall, "category" | "product_name" | "title">) {
  return [recall.category, recall.product_name, recall.title]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("it-IT");
}

function fallbackSelection(key: FallbackKey, label: string): RecallImageSelection {
  return {
    src: FALLBACKS[key],
    label: `Illustrazione standard: ${label}`,
    isFallback: true,
  };
}

/** Prefer trusted source imagery, then choose a deterministic category illustration. */
export function selectRecallImage(recall: Pick<Recall, "image_url" | "category" | "product_name" | "title" | "is_seafood">): RecallImageSelection {
  const sourceImage = safeImageUrl(recall.image_url);
  if (sourceImage) {
    return { src: sourceImage, label: "Immagine dalla fonte del richiamo", isFallback: false };
  }

  if (recall.is_seafood) return fallbackSelection("fish", "prodotti ittici");

  const text = normalizedRecallText(recall);
  const match = MATCHERS.find(({ terms }) => terms.some((term) => text.includes(term)));
  return match ? fallbackSelection(match.key, match.label) : fallbackSelection("generic", "prodotto alimentare");
}
