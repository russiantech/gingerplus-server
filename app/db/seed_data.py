"""Seed content derived from the Southern Rose website content brief. Prices are PLACEHOLDERS — set real ones in Admin → Products."""

PRODUCTS = [
    {
        "name": "Southern Rose Ginger Plus with Turmeric", "slug": "ginger-plus-turmeric", "flavor": "turmeric", "accent_color": "#E8A317",
        "tagline": "Golden wellness in every sip.",
        "short_description": "A bold, golden ginger drink infused with turmeric and a touch of garlic. Naturally anti-inflammatory, rich in antioxidants, and made with fresh Nigerian ginger. No artificial colours.",
        "description": "Golden turmeric meets fiery ginger, with a touch of garlic for depth. Daily wellness for recovery, immunity, and glow.",
        "benefits": ["Supports immunity and recovery", "Natural anti-inflammatory from turmeric and ginger", "Garlic adds depth and immune support", "Rich in gingerols for digestion", "No artificial colours or flavours"],
        "ingredients": "Water, Fresh Ginger, Turmeric, Blackpepper, Garlic, Lemon, Potassium Sorbate.",
        "how_to_enjoy": ["Chilled straight from the bottle", "As a daily wellness drink", "Mixed into cocktails or mocktails"],
        "nutrition": {"Energy": "48 kcal", "Carbohydrates": "12 g", "Protein": "0 g", "Fat": "0 g", "Vitamin B6": "50% DV", "Vitamin C": "30% DV"},
        "storage": "Store in a cool, dry place. Refrigerate after opening. Consume within 3 days of opening.",
        "is_featured": True, "sort_order": 1,
    },
    {
        "name": "Southern Rose Ginger Plus with Honey", "slug": "ginger-plus-honey", "flavor": "honey", "accent_color": "#B7791F",
        "tagline": "Smooth. Soothing. Naturally sweet.",
        "short_description": "Smooth, soothing ginger drink made with Dark Forest Honey and a touch of garlic. Calms the throat and lifts your mood — hot or cold.",
        "description": "Smooth, soothing, made with Dark Forest Honey and a touch of garlic. Calms the throat and lifts your mood — hot or cold.",
        "benefits": ["Soothes the throat", "Natural energy — a gentle lift without a crash", "Garlic and ginger support immunity", "Comforting hot or cold"],
        "ingredients": "Water, Fresh Ginger, Dark Forest Honey, Garlic, Lemon, Potassium Sorbate.",
        "how_to_enjoy": ["Chilled or gently warmed", "As a tea replacement", "In mocktails like the Ginger Fizz"],
        "nutrition": {}, "storage": "Store in a cool, dry place. Refrigerate after opening. Consume within 3 days of opening (350ml) or 2 days (125ml).",
        "is_featured": True, "sort_order": 2,
    },
    {
        "name": "Southern Rose Ginger Plus with Guarana", "slug": "ginger-plus-guarana", "flavor": "guarana", "accent_color": "#5B8C3A",
        "tagline": "Clean energy. Bold ginger.",
        "short_description": "Clean energy from Amazonian guarana, powered by Nigerian ginger. Focus and stamina in every bottle — gentler than coffee, with no jitters.",
        "description": "Clean energy from Amazonian guarana, powered by Nigerian ginger. Focus and stamina in every bottle.",
        "benefits": ["Clean energy from natural caffeine", "Supports mental focus and alertness", "Physical stamina before work or workout", "Gentler than coffee — no jitters"],
        "ingredients": "Water, Fresh Ginger, Guarana, Lemon, Potassium Sorbate.",
        "how_to_enjoy": ["Chilled straight from the bottle", "Before work or a workout", "Mixed with white rum and soda — The Guarana Kick"],
        "nutrition": {}, "storage": "Store in a cool, dry place. Refrigerate after opening. Not recommended for young children (contains natural caffeine).",
        "is_featured": True, "sort_order": 3,
    },
]
SIZES = [
    {"size": "350ml", "count": 24, "label": "350ml · Pack of 24", "price": 18000, "tier": (20, 16500), "sort": 1, "blurb": "Perfect for sharing, retail, and bars."},
    {"size": "125ml", "count": 20, "label": "125ml · Pack of 20", "price": 9000, "tier": (20, 8200), "sort": 2, "blurb": "Perfect for shots, events, and on-the-go."},
]

HERO = [
    {"eyebrow": "Pursuing wellbeing", "title": "Recharge Your Body with Three Powerful Varieties",
     "subtitle": "Made with fresh Nigerian ginger, natural ingredients, and no artificial colours. Available in Turmeric, Honey, and Guarana. Choose 350ml (packed 24) or 125ml (packed 20).",
     "primary_label": "Shop Now", "primary_url": "/shop", "secondary_label": "Wholesale Enquiry", "secondary_url": "/wholesale", "accent_color": "#E8A317", "sort_order": 1},
    {"eyebrow": "Bold Ginger. Perfect Plus.", "title": "Now in Two Sizes — 350ml & 125ml",
     "subtitle": "350ml for sharing, retail and bars. 125ml for shots, events and on-the-go. Same organic ginger, in the size that fits your moment.",
     "primary_label": "Shop Ginger Plus", "primary_url": "/shop", "secondary_label": "Events & Gifting", "secondary_url": "/events-gifting", "accent_color": "#B7791F", "sort_order": 2},
    {"eyebrow": "Bars & Mixers", "title": "The Mixer Your Bar Has Been Waiting For",
     "subtitle": "A strong, natural ginger mixer — perfect for cocktails, shots and mocktails. Tiered wholesale pricing with nationwide delivery.",
     "primary_label": "Request Wholesale Price List", "primary_url": "/wholesale", "secondary_label": "Cocktail Recipes", "secondary_url": "/recipes", "accent_color": "#5B8C3A", "sort_order": 3},
]

def _cards(items): return {"type": "cards", "items": items}

PAGES = [
    {"slug": "about-us", "title": "About Us", "subtitle": "Rooted in Nigeria. Brewed with Purpose.", "show_in_footer": True,
     "blocks": [
        {"type": "richtext", "heading": "Raw Organic ginger. Natural ingredients. Two sizes. Three powerful blends.",
         "body": "Southern Rose was born from a simple belief: that the powerful, natural ingredients growing in our soil can do more than flavour food — they can fuel health, energy, and joy.\n\nWe started with fresh Nigerian ginger. Not extract. Not powder. Real ginger, crushed daily. Then we blended it with turmeric, Dark Forest Honey, and guarana to create three distinct drinks that serve three distinct purposes — wellness, soothing, and energy."},
        {"type": "cards", "heading": "Two convenient sizes", "columns": 2, "items": [
            {"icon": "ri-goblet-line", "title": "350ml", "text": "Perfect for sharing, retail, and bars. Packed 24 per carton."},
            {"icon": "ri-flask-line", "title": "125ml", "text": "Perfect for shots, events, lunchboxes, and on-the-go. Packed 20 per carton."}]},
        {"type": "cards", "heading": "Our Promise", "columns": 3, "items": [
            {"icon": "ri-leaf-line", "title": "Real Ingredients", "text": "Fresh ginger, real turmeric, Dark Forest Honey, pure guarana."},
            {"icon": "ri-shield-check-line", "title": "No Shortcuts", "text": "No artificial colours. No unnecessary additives."},
            {"icon": "ri-heart-pulse-line", "title": "Three Benefits, One Brand", "text": "Wellness. Soothing. Energy."},
            {"icon": "ri-stack-line", "title": "Two Sizes", "text": "350ml and 125ml. For every occasion."},
            {"icon": "ri-map-pin-line", "title": "Made for Nigeria, Ready for the World", "text": "Proudly produced, packed with care."}]},
        {"type": "richtext", "heading": "Our Process", "body": "Every batch begins with fresh organic ginger sourced from local farmers. We crush, macerate, and filter to extract the full spectrum of ginger's active compounds. Then we blend — with turmeric for wellness, Dark Forest Honey for soothing, or guarana for energy. Every bottle is filled, capped, and packed with care."},
        {"type": "richtext", "heading": "Our Vision", "body": "To become Africa's most trusted ginger drink brand — a staple in homes, bars, and stores across the continent and beyond."},
        {"type": "cta", "heading": "Taste the difference", "text": "Real ginger. Real benefits.", "buttons": [{"label": "Shop Our Drinks", "url": "/shop", "variant": "primary"}, {"label": "Contact Us for Wholesale", "url": "/wholesale", "variant": "outline"}]},
     ]},
    {"slug": "our-ingredients", "title": "Our Ingredients", "subtitle": "Real Ingredients. Real Benefits.", "show_in_footer": False,
     "blocks": [
        {"type": "richtext", "body": "Every bottle of Southern Rose Ginger Plus starts with fresh Nigerian ginger — then we add powerful natural ingredients to create three distinct blends."},
        {"type": "cards", "columns": 2, "items": [
            {"icon": "ri-seedling-line", "title": "Fresh Nigerian Ginger", "text": "Sourced from local farmers, crushed daily. Not extract, not powder. This gives our drinks their signature bold, fiery kick.", "meta": [{"label": "What it does", "value": "Warming, digestive, anti-inflammatory"}, {"label": "Key compounds", "value": "Gingerols, shogaols, zingerone"}]},
            {"icon": "ri-sun-line", "title": "Turmeric", "text": "Red Aromatic turmeric adds warmth and wellness to our Turmeric blend.", "meta": [{"label": "What it does", "value": "Anti-inflammatory, antioxidant, supports recovery and immunity"}, {"label": "Key compounds", "value": "Curcuminoids"}]},
            {"icon": "ri-plant-line", "title": "Garlic", "text": "A small amount adds savoury depth and boosts the wellness profile of our Turmeric and Honey blends. You won't taste it as garlic — you'll feel it as fullness.", "meta": [{"label": "What it does", "value": "Immune support, depth of flavour, natural preservation"}, {"label": "Key compounds", "value": "Allicin, ajoene"}]},
            {"icon": "ri-drop-line", "title": "Dark Forest Honey", "text": "Not generic honey — chosen for its deep, complex flavour. It gives our Honey blend a luxurious, rounded taste.", "meta": [{"label": "What it does", "value": "Soothes the throat, natural energy, rich sweetness"}, {"label": "Key compounds", "value": "Natural sugars, enzymes, antioxidants"}]},
            {"icon": "ri-flashlight-line", "title": "Guarana", "text": "Natural caffeine — gentler than coffee, longer-lasting. Ideal for our energy blend.", "meta": [{"label": "What it does", "value": "Clean energy, focus, alertness"}, {"label": "Key compounds", "value": "Guaranine, theobromine, theophylline"}]}]},
        {"type": "richtext", "heading": "No Artificial Colours. No Shortcuts.", "body": "We don't add artificial colours or unnecessary additives. The colour of each drink comes from its natural ingredients — turmeric gold, dark honey amber, guarana green."},
        {"type": "cta", "heading": "Taste real ingredients", "buttons": [{"label": "Shop Now", "url": "/shop", "variant": "primary"}]},
     ]},
    {"slug": "health-benefits", "title": "Health Benefits", "subtitle": "Ginger Plus — Wellness in Every Bottle", "show_in_footer": False,
     "blocks": [
        {"type": "richtext", "body": "Ginger has been used for centuries to support digestion, immunity, and overall health. We've combined it with turmeric, Dark Forest Honey, and guarana to create three functional drinks — each with its own benefit."},
        {"type": "cards", "columns": 3, "items": [
            {"icon": "ri-sun-line", "title": "Turmeric — Wellness & Recovery", "text": "Anti-inflammatory • Antioxidant-rich • Immune support • Aids recovery.", "meta": [{"label": "Best for", "value": "Daily wellness, post-workout, recovery days"}], "link": "/products/ginger-plus-turmeric"},
            {"icon": "ri-drop-line", "title": "Honey — Soothing & Natural Energy", "text": "Soothes the throat • Natural energy without a crash • Immune support • Comforting hot or cold.", "meta": [{"label": "Best for", "value": "Cold relief, tea replacement, everyday refreshment"}], "link": "/products/ginger-plus-honey"},
            {"icon": "ri-flashlight-line", "title": "Guarana — Energy & Focus", "text": "Clean energy • Mental focus • Physical stamina • No jitters — gentler than coffee.", "meta": [{"label": "Best for", "value": "Students, professionals, athletes, long days"}], "link": "/products/ginger-plus-guarana"}]},
        {"type": "cta", "heading": "Find your blend", "buttons": [{"label": "Shop Now", "url": "/shop", "variant": "primary"}]},
     ]},
    {"slug": "bars-mixers", "title": "Bars & Mixers", "subtitle": "The Mixer Your Bar Has Been Waiting For", "show_in_footer": False,
     "blocks": [
        {"type": "richtext", "body": "Southern Rose Ginger Plus is a strong, natural ginger mixer — perfect for cocktails, shots, and mocktails. Available in 350ml (packed 24) and 125ml (packed 20)."},
        {"type": "cards", "heading": "Why Bars Love Southern Rose", "columns": 3, "items": [
            {"icon": "ri-fire-line", "title": "Strong ginger kick", "text": "Made with fresh Nigerian ginger, not extract."},
            {"icon": "ri-palette-line", "title": "Three variants", "text": "Turmeric, Honey, Guarana — each adds a different character."},
            {"icon": "ri-leaf-line", "title": "Real ingredients", "text": "Turmeric, garlic, Dark Forest Honey, guarana."},
            {"icon": "ri-shield-check-line", "title": "No artificial colours", "text": "Clean label."},
            {"icon": "ri-goblet-line", "title": "Two sizes", "text": "350ml for mixing, 125ml for shots."},
            {"icon": "ri-price-tag-3-line", "title": "Attractive wholesale pricing", "text": "Tiered pricing for bars, restaurants and hotels."}]},
        {"type": "richtext", "heading": "Build your own signature cocktails", "body": "Ginger Plus — 125ml Ginger Plus (any variant). Serve chilled."},
        {"type": "list", "heading": "Wholesale for bars, restaurants and hotels", "items": ["350ml packs of 24", "125ml packs of 20", "Tiered wholesale pricing", "Nationwide delivery"]},
        {"type": "cta", "buttons": [{"label": "Request Wholesale Price List", "url": "/wholesale", "variant": "primary"}, {"label": "Cocktail Recipes", "url": "/recipes", "variant": "outline"}]},
     ]},
    {"slug": "events-gifting", "title": "Events & Gifting", "subtitle": "Make Your Event Memorable with Southern Rose", "show_in_footer": False,
     "blocks": [
        {"type": "richtext", "body": "Our 125ml Ginger Plus drinks are perfect for weddings, conferences, parties, and corporate gifting. Packed 20 per carton."},
        {"type": "cards", "heading": "Why 125ml for events?", "columns": 3, "items": [
            {"icon": "ri-hand-heart-line", "title": "Perfect handling size", "text": "No waste, easy to serve."},
            {"icon": "ri-vip-diamond-line", "title": "Elegant presentation", "text": "Clear bottle, natural colours."},
            {"icon": "ri-palette-line", "title": "Three variants", "text": "Something for every guest."},
            {"icon": "ri-leaf-line", "title": "Real ingredients", "text": "Fresh ginger, turmeric, garlic, Dark Forest Honey, guarana."},
            {"icon": "ri-stack-line", "title": "Easy to stack and serve", "text": "20 per carton."},
            {"icon": "ri-brush-line", "title": "Custom labels available", "text": "Add your event name or logo (minimum order applies)."}]},
        {"type": "list", "heading": "Ideal for", "items": ["Weddings", "Conferences", "Corporate events", "Product launches", "Birthdays", "Church events", "Gifting hampers"]},
        {"type": "list", "heading": "Bulk orders for events", "items": ["Discounted pricing for bulk orders", "Custom labels (minimum order applies)", "Delivery to your venue", "Setup and display options (on request)"]},
        {"type": "cta", "buttons": [{"label": "Request Event Quote", "url": "/contact?subject=event", "variant": "primary"}]},
        {"type": "list", "heading": "Corporate gifting", "items": ["Single carton (20 shots)", "Mixed carton (Turmeric, Honey, Guarana)", "Custom branded labels"]},
        {"type": "cta", "text": "Looking for a unique gift for clients or staff? Our 125ml packs make elegant, healthy gift sets.", "buttons": [{"label": "Contact Us for Gifting", "url": "/contact?subject=event", "variant": "primary"}]},
     ]},
    {"slug": "wholesale", "title": "Wholesale & Distribution", "subtitle": "Stock your bar, store, or event with strong Nigerian ginger drinks. Two sizes. Three variants. Attractive margins.", "show_in_footer": True,
     "blocks": [
        {"type": "pricing_table", "heading": "Product Range & Wholesale Pricing"},
        {"type": "list", "heading": "Why stock Southern Rose Ginger Plus?", "items": ["Fast-moving functional beverage with three consumer benefits.", "Two sizes for multiple markets — retail, bars, events.", "Real ingredients: Fresh ginger, turmeric, garlic, Dark Forest Honey, guarana.", "No artificial colours.", "Attractive margins for retailers, bars, and distributors.", "Nationwide delivery. Consistent supply."]},
        {"type": "cards", "heading": "Distributor terms", "columns": 4, "items": [
            {"icon": "ri-stack-line", "title": "Minimum order", "text": "20 packs"}, {"icon": "ri-bank-line", "title": "Payment", "text": "Bank transfer"},
            {"icon": "ri-time-line", "title": "Lead time", "text": "2–5 working days"}, {"icon": "ri-truck-line", "title": "Delivery", "text": "Nationwide"}]},
        {"type": "form", "form": "wholesale", "heading": "Request the wholesale price list"},
        {"type": "cta", "heading": "Become a distributor", "text": "We're expanding across Nigeria. If you have distribution experience and a strong regional network, we'd like to hear from you.", "buttons": [{"label": "Apply to Become a Distributor", "url": "/become-a-distributor", "variant": "primary"}]},
     ]},
    {"slug": "become-a-distributor", "title": "Become a Southern Rose Distributor", "subtitle": "Join our growing network of distributors across Nigeria.", "show_in_footer": True,
     "blocks": [
        {"type": "cards", "heading": "Why partner with Southern Rose?", "columns": 3, "items": [
            {"icon": "ri-flashlight-line", "title": "Fast-moving product", "text": "Strong Nigerian ginger drink with three variants."},
            {"icon": "ri-stack-line", "title": "Two sizes", "text": "350ml (24-pack) and 125ml (20-pack) for multiple markets."},
            {"icon": "ri-line-chart-line", "title": "Attractive margins", "text": "Competitive wholesale pricing."},
            {"icon": "ri-megaphone-line", "title": "Marketing support", "text": "Product images, copy, and social assets provided."},
            {"icon": "ri-truck-line", "title": "Reliable supply", "text": "Consistent production and nationwide delivery."}]},
        {"type": "list", "heading": "What we look for", "items": ["Strong regional network (retailers, bars, supermarkets).", "Ability to meet minimum monthly volumes.", "Storage capacity for bulk orders.", "Some experience and passion in beverage or FMCG distribution."]},
        {"type": "form", "form": "distributor", "heading": "Distributor application"},
        {"type": "steps", "heading": "What happens next?", "items": [
            {"title": "We review your application", "text": "Within 5 working days."}, {"title": "We schedule a call", "text": "To discuss terms."},
            {"title": "We send our price list and agreement", "text": "Distributor price list and agreement."}, {"title": "You place your first order", "text": "And start selling."}]},
     ]},
    {"slug": "media-press", "title": "Media & Press", "subtitle": "For press enquiries, brand assets, and media requests, please contact us.", "show_in_footer": False,
     "blocks": [
        {"type": "richtext", "heading": "About Southern Rose", "body": "Southern Rose produces bold, natural ginger drinks under the Ginger Plus brand. Available in Turmeric, Honey, and Guarana variants, in 350ml (24-pack) and 125ml (20-pack) sizes. Made in Nigeria with fresh Nigerian ginger, Dark Forest Honey, and no artificial colours."},
        {"type": "cards", "heading": "Brand assets", "columns": 3, "items": [
            {"icon": "ri-image-line", "title": "Logo Pack", "text": "PNG, JPG, SVG", "link": "#"}, {"icon": "ri-camera-line", "title": "Product Images", "text": "High-resolution photos", "link": "#"},
            {"icon": "ri-file-pdf-line", "title": "Brand Guidelines", "text": "PDF", "link": "#"}]},
        {"type": "cards", "heading": "Press releases", "columns": 2, "items": [
            {"icon": "ri-newspaper-line", "title": "Launch: Southern Rose Ginger Plus", "text": "Read the press release", "link": "#"},
            {"icon": "ri-newspaper-line", "title": "New: 125ml GingerPlus Packs", "text": "Read the press release", "link": "#"}]},
        {"type": "richtext", "heading": "Media contact", "body": "For interviews, samples, or press enquiries:\nEmail: nolpartnership2015@gmail.com\nPhone: +2349035483698\nInstagram | Facebook | TikTok: @gingerplus_biorefinery"},
     ]},
    {"slug": "privacy-policy", "title": "Privacy Policy", "subtitle": "Last updated: 2026", "show_in_footer": True,
     "blocks": [{"type": "legal", "sections": [
        {"title": "1. Introduction", "body": "Southern Rose (\"we\", \"our\", \"us\") respects your privacy. This policy explains how we collect, use, and protect your personal information when you visit our website or place an order."},
        {"title": "2. Information We Collect", "body": "• Name, email, phone number, delivery address\n• Payment details (processed securely by our payment partners)\n• Order history\n• Website usage data (cookies, analytics)"},
        {"title": "3. How We Use Your Information", "body": "• To process and deliver your orders\n• To communicate about your order\n• To send marketing updates (only with your consent)\n• To improve our website and products"},
        {"title": "4. Sharing Your Information", "body": "We do not sell your data. We may share it with delivery partners, payment processors, and legal authorities if required by law."},
        {"title": "5. Data Security", "body": "We use industry-standard measures to protect your data. However, no online transmission is 100% secure."},
        {"title": "6. Cookies", "body": "Our website uses cookies to improve your experience. You can disable cookies in your browser settings."},
        {"title": "7. Your Rights", "body": "You may request access, correction, or deletion of your personal data by contacting us at southernrose.enueshike@gmail.com."},
        {"title": "8. Changes to This Policy", "body": "We may update this policy. Changes will be posted on this page."},
        {"title": "9. Contact", "body": "For privacy questions: southernrose.enueshike@gmail.com"}]}]},
    {"slug": "terms-and-conditions", "title": "Terms & Conditions", "subtitle": "Last updated: 2026", "show_in_footer": True,
     "blocks": [{"type": "legal", "sections": [
        {"title": "1. Acceptance", "body": "By using our website or placing an order, you agree to these terms."},
        {"title": "2. Products", "body": "All products are subject to availability. Images are for illustration; actual product may vary slightly."},
        {"title": "3. Pricing", "body": "Prices are listed in Nigerian Naira (₦) and may change without notice. We reserve the right to correct pricing errors."},
        {"title": "4. Orders", "body": "• Orders are confirmed once payment is received.\n• We reserve the right to cancel orders if products are unavailable or if fraud is suspected."},
        {"title": "5. Payment", "body": "We accept bank transfer, Paystack, and other listed methods. Payment must be completed before dispatch."},
        {"title": "6. Delivery", "body": "• Delivery timelines are estimates, not guarantees.\n• Risk passes to you upon delivery.\n• Delivery fees are shown at checkout."},
        {"title": "7. Returns & Refunds", "body": "See our Shipping & Returns page."},
        {"title": "8. Intellectual Property", "body": "All content on this website (logos, text, images) is owned by Southern Rose and may not be used without permission."},
        {"title": "9. Limitation of Liability", "body": "We are not liable for indirect or consequential losses arising from use of our products or website."},
        {"title": "10. Governing Law", "body": "These terms are governed by the laws of the Federal Republic of Nigeria."},
        {"title": "11. Contact", "body": "For questions: southernrose.enueshike@gmail.com"}]}]},
    {"slug": "shipping-returns", "title": "Shipping & Returns", "subtitle": "Nationwide delivery across Nigeria", "show_in_footer": True,
     "blocks": [{"type": "legal", "sections": [
        {"title": "Delivery areas", "body": "We deliver nationwide across Nigeria."},
        {"title": "Delivery times", "body": "• Lagos: 1–2 working days\n• Other states: 2–5 working days\n• Remote areas: 5–7 working days"},
        {"title": "Delivery fees", "body": "Calculated at checkout based on location and order size."},
        {"title": "Order processing", "body": "Orders are processed within 24 hours of payment confirmation (Mon–Fri)."},
        {"title": "Bulk orders", "body": "For large or wholesale orders, contact us for a custom delivery quote."},
        {"title": "Damaged or incorrect items", "body": "If your order arrives damaged or incorrect, contact us within 48 hours with photos. We'll replace or refund."},
        {"title": "Non-returnable items", "body": "For health and safety reasons, opened bottles cannot be returned."},
        {"title": "Refund process", "body": "Approved refunds are processed within 5–7 working days to your original payment method."},
        {"title": "Cancellations", "body": "Orders can be cancelled before dispatch. Contact us immediately."},
        {"title": "Contact for shipping & returns", "body": "WhatsApp: +234 802 772 4193\nEmail: southernrose.enueshike@gmail.com"}]}]},
]

FAQS = [
    ("What is Southern Rose Ginger Plus?", "A strong, natural ginger drink made with fresh Nigerian ginger. Available in three variants: Turmeric, Honey, and Guarana.", "Product"),
    ("What sizes do you sell?", "We sell 350ml bottles (packed 24 per carton) and 125ml bottles (packed 20 per carton).", "Product"),
    ("What's the difference between 350ml and 125ml?", "Same drink, different size. 350ml is for sharing, retail, and bars. 125ml is for shots, sampling, lunchboxes, gyms, and events.", "Product"),
    ("Does it contain garlic?", "Yes. Our Turmeric and Honey blends contain a small amount of garlic for depth and immune support. You won't taste it as garlic — it adds fullness. The Guarana blend does not contain garlic.", "Product"),
    ("What kind of honey do you use?", "We use Dark Forest Honey, not generic honey. It gives our Honey blend a rich, complex flavour.", "Product"),
    ("Do you sell single bottles?", "We primarily sell by the pack. Single bottles may be available for sampling — contact us.", "Ordering"),
    ("Where can I buy Southern Rose Ginger Plus?", "Directly from our website, via WhatsApp, or from selected retailers and bars.", "Ordering"),
    ("Do you offer wholesale prices?", "Yes. We have tiered wholesale pricing for bars, retailers, and distributors.", "Wholesale"),
    ("How should I store the drink?", "Store in a cool, dry place. Refrigerate after opening and consume within 3 days for 350ml, or 2 days for 125ml.", "Product"),
    ("Does it contain artificial colours?", "No. Our colours come from natural ingredients — turmeric, Dark Forest Honey, and guarana.", "Product"),
    ("Is it safe for children?", "The Turmeric and Honey variants are generally suitable for children. The Guarana variant contains natural caffeine and is not recommended for young children.", "Product"),
    ("Does it contain alcohol?", "No. Southern Rose Ginger Plus is a non-alcoholic drink.", "Product"),
    ("Can I use it as a mixer?", "Absolutely. It's a favourite mixer for cocktails.", "Product"),
    ("How long does delivery take?", "Nationwide delivery typically takes 2–5 working days.", "Delivery"),
    ("How do I place a wholesale order?", "WhatsApp or email us with your order quantity and delivery location — or order online and choose wholesale at checkout.", "Wholesale"),
    ("Can I become a distributor?", "Yes. Contact us with your region and expected monthly volume, or apply on our Become a Distributor page.", "Wholesale"),
    ("Can I mix sizes in one order?", "Yes. You can order any combination of 350ml and 125ml packs.", "Ordering"),
]

TESTIMONIALS = [
    ("Ubong", "Bar Owner — Lagos", "Dajessy Lounge", "Southern Rose Ginger Plus has become a staple in our cocktails. The Turmeric and Guarana blend is perfect for mixing. Our customers ask for it by name."),
    ("Sylvester", "Wholesaler — Abuja", "Sylgro Infinite Nig Ltd", "The 125ml packs sell fast. Customers love the shot size and the natural ingredients. Reordering every week."),
    ("Ebele", "Customer — Port Harcourt", None, "I drink the Turmeric blend every morning. It helps me empty my bowel and I love that there's no artificial colour."),
    ("Mrs. Ajayi", "Event Planner — Lagos", None, "We used the 125ml Gingerplus at my grandma's 90th Birthday Celebration. They looked elegant and the guests loved them. Will definitely order again."),
    ("Kayode", "Gym Owner — Akure", "Femaplast Nig Ltd", "Our members love the Guarana blend before workouts. Clean energy, no jitters."),
]

RECIPES = [
    ("The Southern Mule", "cocktail", "honey", "Vodka, Ginger Plus with Honey, fresh lime, ice.", ["50ml vodka", "125ml Ginger Plus with Honey", "Juice of ½ fresh lime", "Ice"], ["Fill a copper mug or tall glass with ice.", "Add vodka and lime juice.", "Top with chilled Ginger Plus with Honey and stir gently.", "Garnish with a lime wheel."]),
    ("The Dark & Stormy Rose", "cocktail", "turmeric", "Dark rum, Ginger Plus with Turmeric, lime wedge.", ["50ml dark rum", "125ml Ginger Plus with Turmeric", "Lime wedge", "Ice"], ["Fill a highball glass with ice.", "Pour in the dark rum.", "Top with Ginger Plus with Turmeric.", "Squeeze in a lime wedge and drop it in."]),
    ("The Guarana Kick", "cocktail", "guarana", "White rum, Ginger Plus with Guarana, soda.", ["50ml white rum", "100ml Ginger Plus with Guarana", "Splash of soda", "Ice"], ["Add ice and rum to a tall glass.", "Pour in Ginger Plus with Guarana.", "Finish with a splash of soda."]),
    ("Warm Turmeric Tonic", "warm_drink", "turmeric", "Ginger Plus with Turmeric, honey, lemon. Sip slowly.", ["250ml Ginger Plus with Turmeric", "1 tsp honey", "Squeeze of lemon"], ["Warm the Ginger Plus gently — do not boil.", "Stir in honey and lemon.", "Sip slowly."]),
    ("Honey Ginger Soother", "warm_drink", "honey", "Ginger Plus with Honey, warmed gently. Perfect for cold days.", ["250ml Ginger Plus with Honey"], ["Warm gently in a saucepan until steaming.", "Pour into a mug and enjoy."]),
    ("The Classic Ginger Shot", "shot", None, "125ml Ginger Plus (any variant), chilled.", ["125ml Ginger Plus (any variant)"], ["Chill the bottle.", "Serve straight."]),
    ("The Wellness Shot", "shot", "turmeric", "125ml Turmeric Ginger Plus, squeeze of lemon.", ["125ml Ginger Plus with Turmeric", "Squeeze of lemon"], ["Pour chilled Turmeric Ginger Plus.", "Add a squeeze of lemon."]),
    ("The Energy Shot", "shot", "guarana", "125ml Guarana Ginger Plus, chilled.", ["125ml Ginger Plus with Guarana"], ["Serve well chilled."]),
    ("Ginger Fizz", "mocktail", "honey", "Ginger Plus with Honey, sparkling water, lime.", ["100ml Ginger Plus with Honey", "100ml sparkling water", "Lime wedge", "Ice"], ["Fill a glass with ice.", "Add Ginger Plus and sparkling water.", "Squeeze in lime."]),
    ("Turmeric Sunrise", "mocktail", "turmeric", "Ginger Plus with Turmeric, orange juice, ice.", ["100ml Ginger Plus with Turmeric", "100ml orange juice", "Ice"], ["Fill a glass with ice.", "Add orange juice, then slowly pour the Ginger Plus on top."]),
]

BLOG = [
    ("3 Ways to Enjoy Southern Rose Ginger Plus (Beyond Drinking It Straight)", "Recipes", True, "Southern Rose Ginger Plus is delicious on its own — but it's also a versatile mixer and wellness companion. Here are three ways to enjoy it.",
     "Southern Rose Ginger Plus is delicious on its own — but it's also a versatile mixer and wellness companion.\n\n**1. As a cocktail mixer.** Pair Honey with vodka for a Southern Mule, or Turmeric with dark rum for a Dark & Stormy Rose.\n\n**2. As a warm tonic.** Warm Ginger Plus with Honey gently for a soothing evening drink, or add lemon to the Turmeric blend.\n\n**3. As a daily shot.** Keep a few 125ml bottles in the fridge for a quick wellness or energy shot."),
    ("How to Store Your Ginger Plus", "Wellness", False, "Keep your drinks fresh and flavourful with these simple storage tips.", "Store unopened bottles in a cool, dry place. Once opened, refrigerate and consume within 3 days for 350ml, or 2 days for 125ml."),
    ("Why Nigerian Ginger is the Best in the World", "Ingredients", False, "Nigeria produces some of the most potent, flavourful ginger on the planet. Here's why.", "Nigerian ginger is prized for its pungency and high concentration of gingerols and shogaols — the compounds behind ginger's famous kick and benefits. At Southern Rose we source from local farmers and crush the ginger fresh, daily."),
    ("Ginger for Wellness: What Science Says", "Wellness", False, "A look at the research behind ginger's anti-inflammatory and digestive benefits.", "Ginger has been used for centuries to support digestion and overall health. Research has examined its active compounds — gingerols, shogaols and zingerone — for anti-inflammatory and digestive effects. Southern Rose Ginger Plus is a food drink, not a medicine; speak to your doctor about any health condition."),
    ("The Story Behind Southern Rose", "Brand Story", False, "How we started, why we chose ginger, and where we're going.", "Southern Rose was born from a simple belief: that the powerful, natural ingredients growing in our soil can do more than flavour food. We started with fresh Nigerian ginger and built three blends around it. Our vision is to become Africa's most trusted ginger drink brand."),
    ("125ml Shots: Perfect for Events, Gyms, and Lunchboxes", "Events", False, "Why we introduced the 125ml size — and how to use it.", "The 125ml bottle is the perfect handling size for shots, sampling, lunchboxes, gyms and events — packed 20 per carton, in all three variants."),
]

CATEGORIES = [
    ("Ginger Plus Drinks", "ginger-drinks", "Three bold blends. Two sizes.", 1),
    ("Events & Gifting", "events-gifting", "Gift sets and event packs.", 2),
    ("Merchandise", "merchandise", "Branded bar & event merchandise (coming soon).", 3),
]

# state -> (fee, min_days, max_days)
LAGOS = {"Lagos": (2500, 1, 2)}
SW = {s: (3500, 2, 3) for s in ["Ogun", "Oyo", "Osun", "Ondo", "Ekiti"]}
REMOTE = {s: (7500, 5, 7) for s in ["Borno", "Yobe", "Adamawa", "Taraba", "Sokoto", "Zamfara", "Kebbi", "Bayelsa"]}

