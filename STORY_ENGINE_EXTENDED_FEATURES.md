# 🚀 Story Engine - Extended Features

**Доповнення до STORY_ENGINE_REDESIGN.md**
**Date:** 2026-02-20

---

## 📋 TABLE OF CONTENTS

1. [Comprehensive Dropdowns для Story Engine](#comprehensive-dropdowns)
2. [Content Topics Queue Manager](#content-topics-queue)
3. [DynamoDB Schema для Topics](#topics-dynamodb-schema)
4. [Lambda Functions для Topics](#topics-lambda-functions)
5. [UI Components](#ui-components)
6. [Integration з Step Functions](#step-functions-integration)

---

## 1️⃣ COMPREHENSIVE DROPDOWNS ДЛЯ STORY ENGINE

### **ВАЖЛИВО:** Всі текстові поля замінити на випадаючі списки з великою кількістю опцій!

### **1.1 World Type (Тип світу)**

```html
<select id="world_type">
  <option value="">— Оберіть тип світу —</option>

  <optgroup label="🌍 Реалістичні">
    <option value="modern_realistic">Modern Realistic (сучасний світ)</option>
    <option value="historical_realistic">Historical Realistic (історичний світ)</option>
    <option value="contemporary_drama">Contemporary Drama (сучасна драма)</option>
    <option value="small_town">Small Town (маленьке містечко)</option>
    <option value="big_city">Big City (велике місто)</option>
  </optgroup>

  <optgroup label="✨ Фентезі">
    <option value="medieval_fantasy">Medieval Fantasy (середньовіччя + магія)</option>
    <option value="urban_fantasy">Urban Fantasy (сучасний світ + магія)</option>
    <option value="dark_fantasy">Dark Fantasy (темне фентезі)</option>
    <option value="epic_fantasy">Epic Fantasy (епічне фентезі)</option>
    <option value="fairy_tale">Fairy Tale (казка)</option>
    <option value="sword_and_sorcery">Sword & Sorcery (меч і чаклунство)</option>
  </optgroup>

  <optgroup label="🚀 Наукова фантастика">
    <option value="cyberpunk">Cyberpunk (майбутнє + корпорації)</option>
    <option value="space_opera">Space Opera (космос + подорожі)</option>
    <option value="dystopian">Dystopian (антиутопія)</option>
    <option value="utopian">Utopian (утопія)</option>
    <option value="post_apocalyptic">Post-Apocalyptic (після апокаліпсису)</option>
    <option value="steampunk">Steampunk (вікторіанська епоха + технології)</option>
    <option value="dieselpunk">Dieselpunk (1920-50-ті + технології)</option>
    <option value="solarpunk">Solarpunk (екологічне майбутнє)</option>
  </optgroup>

  <optgroup label="🔮 Альтернативні">
    <option value="alternate_history">Alternate History (альтернативна історія)</option>
    <option value="parallel_universe">Parallel Universe (паралельний всесвіт)</option>
    <option value="supernatural">Supernatural (надприродне)</option>
    <option value="mythological">Mythological (міфологія)</option>
    <option value="dreamscape">Dreamscape (світ снів)</option>
  </optgroup>

  <optgroup label="👻 Жахи">
    <option value="horror_gothic">Gothic Horror (готичний жах)</option>
    <option value="horror_cosmic">Cosmic Horror (космічний жах)</option>
    <option value="horror_psychological">Psychological Horror (психологічний)</option>
    <option value="horror_supernatural">Supernatural Horror (надприродний)</option>
    <option value="horror_body">Body Horror (тілесний жах)</option>
    <option value="horror_survival">Survival Horror (жах виживання)</option>
  </optgroup>

  <optgroup label="🕵️ Детектив/Трилер">
    <option value="noir">Noir (чорний детектив)</option>
    <option value="whodunit">Whodunit (хто вбивця?)</option>
    <option value="spy_thriller">Spy Thriller (шпигунський трилер)</option>
  </optgroup>
</select>
```

---

### **1.2 Tone (Емоційний тон)**

```html
<select id="tone">
  <option value="">— Оберіть емоційний тон —</option>

  <optgroup label="🌑 Темні тони">
    <option value="dark">Dark (темний, похмурий)</option>
    <option value="disturbing">Disturbing (тривожний, моторошний)</option>
    <option value="grim">Grim (похмурий, безнадійний)</option>
    <option value="sinister">Sinister (зловісний)</option>
    <option value="melancholic">Melancholic (меланхолійний)</option>
    <option value="bleak">Bleak (безрадісний)</option>
    <option value="ominous">Ominous (зловісний, передвісний)</option>
  </optgroup>

  <optgroup label="💔 Емоційні тони">
    <option value="emotional">Emotional (емоційний, зворушливий)</option>
    <option value="dramatic">Dramatic (драматичний)</option>
    <option value="intense">Intense (напружений)</option>
    <option value="passionate">Passionate (пристрасний)</option>
    <option value="heartfelt">Heartfelt (щирий)</option>
    <option value="poignant">Poignant (зворушливий)</option>
  </optgroup>

  <optgroup label="⚔️ Епічні тони">
    <option value="epic">Epic (епічний, грандіозний)</option>
    <option value="heroic">Heroic (героїчний)</option>
    <option value="triumphant">Triumphant (тріумфальний)</option>
    <option value="grand">Grand (величний)</option>
    <option value="legendary">Legendary (легендарний)</option>
  </optgroup>

  <optgroup label="☮️ Спокійні тони">
    <option value="calm">Calm (спокійний)</option>
    <option value="contemplative">Contemplative (споглядальний)</option>
    <option value="serene">Serene (безтурботний)</option>
    <option value="peaceful">Peaceful (мирний)</option>
    <option value="meditative">Meditative (медитативний)</option>
  </optgroup>

  <optgroup label="🎭 Інтригуючі тони">
    <option value="mysterious">Mysterious (таємничий)</option>
    <option value="suspenseful">Suspenseful (напружений з інтригою)</option>
    <option value="enigmatic">Enigmatic (загадковий)</option>
    <option value="uncanny">Uncanny (моторошно-незвичайний)</option>
  </optgroup>

  <optgroup label="🌈 Світлі тони">
    <option value="hopeful">Hopeful (оптимістичний)</option>
    <option value="uplifting">Uplifting (піднесений)</option>
    <option value="inspiring">Inspiring (надихаючий)</option>
    <option value="joyful">Joyful (радісний)</option>
  </optgroup>

  <optgroup label="🎪 Незвичайні тони">
    <option value="whimsical">Whimsical (химерний, казковий)</option>
    <option value="surreal">Surreal (сюрреалістичний)</option>
    <option value="absurd">Absurd (абсурдний)</option>
    <option value="satirical">Satirical (сатиричний)</option>
  </optgroup>

  <optgroup label="💫 Змішані тони">
    <option value="bittersweet">Bittersweet (гірко-солодкий)</option>
    <option value="ironic">Ironic (іронічний)</option>
    <option value="tragicomic">Tragicomic (трагікомічний)</option>
    <option value="nostalgic">Nostalgic (ностальгічний)</option>
  </optgroup>
</select>
```

---

### **1.3 Narrative Pace (Темп розповіді)**

```html
<select id="narrative_pace">
  <option value="">— Оберіть темп розповіді —</option>
  <option value="very_slow">⏳ Very Slow (дуже повільний - атмосфера, деталі)</option>
  <option value="slow">🐌 Slow (повільний - заглиблення в деталі)</option>
  <option value="moderate">⚖️ Moderate (помірний - баланс)</option>
  <option value="fast">⚡ Fast (швидкий - динаміка, події)</option>
  <option value="very_fast">🚀 Very Fast (дуже швидкий - екшн, адреналін)</option>
  <option value="variable">🌊 Variable (змінний - залежить від сцени)</option>
  <option value="crescendo">📈 Crescendo (поступове прискорення)</option>
  <option value="decrescendo">📉 Decrescendo (поступове уповільнення)</option>
</select>
```

---

### **1.4 Plot Structure Template (Структура сюжету)**

```html
<select id="plot_structure_template">
  <option value="">— Оберіть структуру сюжету —</option>

  <optgroup label="📚 Класичні структури">
    <option value="three_act">Three-Act Structure (3-актна)</option>
    <option value="five_act">Five-Act Structure (5-актна шекспірівська)</option>
    <option value="heros_journey">Hero's Journey (подорож героя - 12 етапів)</option>
    <option value="freytag_pyramid">Freytag's Pyramid (піраміда Фрейтага)</option>
    <option value="seven_point">Seven-Point Story Structure</option>
  </optgroup>

  <optgroup label="🎬 Сучасні структури">
    <option value="save_the_cat">Save the Cat (15 beats)</option>
    <option value="story_circle">Story Circle (Дена Хармона - 8 етапів)</option>
    <option value="fichtean_curve">Fichtean Curve (крива Фіхте - багато криз)</option>
    <option value="snowflake">Snowflake Method</option>
  </optgroup>

  <optgroup label="🕵️ Жанрові структури">
    <option value="mystery">Mystery Structure (детектив - підказки + розкриття)</option>
    <option value="horror">Horror Structure (жахи - нагнітання + кульмінація)</option>
    <option value="romance">Romance Structure (романтика - зустріч + перешкоди + возз'єднання)</option>
    <option value="thriller">Thriller Structure (трилер - інтрига + напруга)</option>
    <option value="tragedy">Tragedy Structure (трагедія - фатальна помилка)</option>
  </optgroup>

  <optgroup label="🎭 Спеціальні структури">
    <option value="in_medias_res">In Medias Res (починається з середини - кульмінації)</option>
    <option value="circular">Circular (коло - кінець повертається до початку)</option>
    <option value="nonlinear">Nonlinear (нелінійна розповідь - стрибки в часі)</option>
    <option value="frame_story">Frame Story (історія в історії)</option>
    <option value="episodic">Episodic (епізодична - окремі події)</option>
    <option value="parallel">Parallel Stories (паралельні історії)</option>
    <option value="reverse_chronology">Reverse Chronology (зворотна хронологія)</option>
  </optgroup>

  <optgroup label="⚡ Експериментальні">
    <option value="rashomon">Rashomon (багато точок зору на одну подію)</option>
    <option value="mosaic">Mosaic (мозаїка - фрагменти складаються в картину)</option>
    <option value="hyperlink">Hyperlink Cinema (взаємопов'язані історії)</option>
  </optgroup>
</select>
```

---

### **1.5 Character Archetype (Архетип персонажа)**

```html
<select id="character_archetype">
  <option value="">— Оберіть архетип головного персонажа —</option>

  <optgroup label="⚔️ Героїчні архетипи">
    <option value="hero">Hero (класичний герой)</option>
    <option value="anti_hero">Anti-Hero (антигерой)</option>
    <option value="reluctant_hero">Reluctant Hero (вимушений герой)</option>
    <option value="tragic_hero">Tragic Hero (трагічний герой)</option>
    <option value="byronic_hero">Byronic Hero (байронівський герой)</option>
  </optgroup>

  <optgroup label="🧠 Інтелектуальні архетипи">
    <option value="sage">Sage (мудрець)</option>
    <option value="scholar">Scholar (вчений)</option>
    <option value="detective">Detective (детектив)</option>
    <option value="broken_genius">Broken Genius (зламаний геній)</option>
    <option value="mad_scientist">Mad Scientist (божевільний вчений)</option>
    <option value="philosopher">Philosopher (філософ)</option>
  </optgroup>

  <optgroup label="🛡️ Захисники">
    <option value="guardian">Guardian (охоронець)</option>
    <option value="mentor">Mentor (наставник)</option>
    <option value="caregiver">Caregiver (той хто піклується)</option>
    <option value="warrior">Warrior (воїн)</option>
    <option value="paladin">Paladin (паладин - святий воїн)</option>
    <option value="protector">Protector (захисник)</option>
  </optgroup>

  <optgroup label="🏴 Вільні духом">
    <option value="rebel">Rebel (бунтар)</option>
    <option value="explorer">Explorer (дослідник)</option>
    <option value="outlaw">Outlaw (злочинець з кодексом)</option>
    <option value="wanderer">Wanderer (мандрівник)</option>
    <option value="free_spirit">Free Spirit (вільний дух)</option>
    <option value="adventurer">Adventurer (шукач пригод)</option>
  </optgroup>

  <optgroup label="🌸 Невинні">
    <option value="innocent">Innocent (невинний)</option>
    <option value="orphan">Orphan (сирота)</option>
    <option value="child">Child (дитина)</option>
    <option value="idealist">Idealist (ідеаліст)</option>
  </optgroup>

  <optgroup label="😈 Темні архетипи">
    <option value="villain_pov">Villain POV (антагоніст головний герой)</option>
    <option value="shadow">Shadow (тінь)</option>
    <option value="trickster">Trickster (обманщик)</option>
    <option value="fallen_hero">Fallen Hero (впалий герой)</option>
    <option value="corrupted">Corrupted (зіпсований)</option>
    <option value="vengeful">Vengeful (мстивий)</option>
  </optgroup>

  <optgroup label="💔 Жертви долі">
    <option value="survivor">Survivor (той хто вижив)</option>
    <option value="victim">Victim (жертва)</option>
    <option value="haunted">Haunted (переслідуваний минулим)</option>
    <option value="cursed">Cursed (проклятий)</option>
    <option value="martyr">Martyr (мученик)</option>
  </optgroup>

  <optgroup label="👥 Соціальні архетипи">
    <option value="everyman">Everyman (звичайна людина)</option>
    <option value="lover">Lover (закоханий)</option>
    <option value="creator">Creator (творець)</option>
    <option value="ruler">Ruler (правитель)</option>
    <option value="jester">Jester (блазень)</option>
    <option value="diplomat">Diplomat (дипломат)</option>
  </optgroup>

  <optgroup label="🎭 Складні архетипи">
    <option value="shapeshifter">Shapeshifter (той хто змінюється)</option>
    <option value="herald">Herald (вісник)</option>
    <option value="threshold_guardian">Threshold Guardian (страж порогу)</option>
    <option value="wild_card">Wild Card (дика карта)</option>
  </optgroup>
</select>
```

---

### **1.6 Primary Conflict Type (Тип конфлікту)**

```html
<select id="primary_conflict_type">
  <option value="">— Оберіть основний тип конфлікту —</option>

  <optgroup label="🤼 Зовнішні конфлікти">
    <option value="man_vs_man">Man vs Man (людина проти людини)</option>
    <option value="man_vs_society">Man vs Society (людина проти суспільства)</option>
    <option value="man_vs_nature">Man vs Nature (людина проти природи)</option>
    <option value="man_vs_technology">Man vs Technology (людина проти технологій)</option>
    <option value="man_vs_supernatural">Man vs Supernatural (людина проти надприродного)</option>
    <option value="man_vs_fate">Man vs Fate (людина проти долі)</option>
    <option value="man_vs_god">Man vs God (людина проти бога/богів)</option>
    <option value="man_vs_system">Man vs System (людина проти системи)</option>
  </optgroup>

  <optgroup label="🧠 Внутрішні конфлікти">
    <option value="man_vs_self">Man vs Self (внутрішній конфлікт)</option>
    <option value="moral_dilemma">Moral Dilemma (моральна дилема)</option>
    <option value="identity_crisis">Identity Crisis (криза ідентичності)</option>
    <option value="internal_struggle">Internal Struggle (внутрішня боротьба)</option>
    <option value="guilt">Guilt (провина)</option>
    <option value="addiction">Addiction (залежність)</option>
  </optgroup>

  <optgroup label="🌐 Комбіновані">
    <option value="multi_layered">Multi-Layered (багатошаровий конфлікт)</option>
    <option value="evolving">Evolving (конфлікт що еволюціонує)</option>
    <option value="parallel_conflicts">Parallel Conflicts (паралельні конфлікти)</option>
  </optgroup>
</select>
```

---

### **1.7 Preferred Ending Type (Тип кінцівки)**

```html
<select id="preferred_ending_type">
  <option value="">— Оберіть тип кінцівки —</option>

  <optgroup label="✨ Позитивні кінцівки">
    <option value="happy">Happy Ending (щасливий кінець)</option>
    <option value="hopeful">Hopeful Ending (з надією на краще)</option>
    <option value="triumphant">Triumphant Ending (тріумф)</option>
    <option value="redemptive">Redemptive Ending (спокута, викуплення)</option>
    <option value="uplifting">Uplifting Ending (піднесений)</option>
  </optgroup>

  <optgroup label="💀 Негативні кінцівки">
    <option value="tragic">Tragic Ending (трагічний)</option>
    <option value="dark">Dark Ending (темний)</option>
    <option value="devastating">Devastating Ending (руйнівний)</option>
    <option value="pyrrhic_victory">Pyrrhic Victory (пірова перемога)</option>
    <option value="apocalyptic">Apocalyptic Ending (апокаліптичний)</option>
    <option value="nihilistic">Nihilistic Ending (нігілістичний)</option>
  </optgroup>

  <optgroup label="❓ Відкриті кінцівки">
    <option value="open">Open Ending (відкритий фінал)</option>
    <option value="cliffhanger">Cliffhanger (кліфхенгер для продовження)</option>
    <option value="ambiguous">Ambiguous Ending (неоднозначний)</option>
    <option value="unresolved">Unresolved Ending (невирішений)</option>
  </optgroup>

  <optgroup label="🎭 Несподівані кінцівки">
    <option value="twist">Twist Ending (поворот сюжету)</option>
    <option value="shocking">Shocking Ending (шокуючий)</option>
    <option value="revelation">Revelation Ending (розкриття таємниці)</option>
    <option value="reversal">Reversal Ending (переворот ситуації)</option>
  </optgroup>

  <optgroup label="💫 Змішані кінцівки">
    <option value="bittersweet">Bittersweet Ending (гірко-солодкий)</option>
    <option value="ironic">Ironic Ending (іронічний)</option>
    <option value="circular">Circular Ending (коло - повернення до початку)</option>
    <option value="metamorphic">Metamorphic Ending (трансформація)</option>
  </optgroup>

  <optgroup label="🔮 Філософські кінцівки">
    <option value="existential">Existential Ending (екзистенціальний)</option>
    <option value="symbolic">Symbolic Ending (символічний)</option>
    <option value="allegorical">Allegorical Ending (алегоричний)</option>
  </optgroup>
</select>
```

---

## 2️⃣ CONTENT TOPICS QUEUE MANAGER

### **Концепція:**
Система управління чергою тем для автоматичної генерації контенту. Користувач може:
1. **Manually додати** теми (по одній)
2. **AI-генерація** тем (наприклад, "згенеруй 50 тем для horror каналу")
3. **Завантажити з файлу** (CSV/TXT - до 100 тем)
4. **Переглядати статус** кожної теми (pending / in_progress / completed / failed)
5. **Видаляти / редагувати** теми
6. **Пріоритизувати** теми (drag-and-drop або стрілки вгору/вниз)

---

### **2.1 UI Block - Topics Queue Manager**

```html
<!-- Section 4.8: CONTENT TOPICS QUEUE -->
<div class="config-section">
  <h2>📋 Content Topics Queue Manager</h2>
  <p>Керуйте чергою тем для автоматичної генерації контенту (до 100 тем)</p>

  <!-- Progress Bar -->
  <div class="topics-progress">
    <div class="progress-bar">
      <div class="progress-fill" id="topics-progress-fill" style="width: 15%;"></div>
    </div>
    <div class="progress-stats">
      <span id="topics-completed-count">15</span> / <span id="topics-total-count">100</span> тем використано
      <span class="progress-percentage">(15%)</span>
    </div>
  </div>

  <!-- Add Topic Manually -->
  <div class="add-topic-section">
    <h3>➕ Додати тему вручну</h3>
    <div class="input-group">
      <input
        type="text"
        id="manual-topic-input"
        placeholder="Наприклад: The Haunted Lighthouse of Lost Souls"
        maxlength="200"
      >
      <button class="btn-primary" onclick="addTopicManually()">
        <i class="bi bi-plus-circle"></i> Додати
      </button>
    </div>
  </div>

  <!-- Generate Topics with AI -->
  <div class="generate-topics-section">
    <h3>🤖 Згенерувати теми за допомогою AI</h3>
    <div class="input-group">
      <input
        type="number"
        id="generate-topics-count"
        min="1"
        max="100"
        value="20"
        placeholder="Кількість тем"
      >
      <input
        type="text"
        id="generate-topics-context"
        placeholder="Додатковий контекст (опціонально)"
        style="flex: 2;"
      >
      <button class="btn-ai" onclick="generateTopicsWithAI()">
        <i class="bi bi-stars"></i> Згенерувати
      </button>
    </div>
    <small style="color: #6b7280; display: block; margin-top: 8px;">
      AI згенерує теми на основі налаштувань каналу (жанр, тон, world type)
    </small>
  </div>

  <!-- Upload Topics from File -->
  <div class="upload-topics-section">
    <h3>📁 Завантажити теми з файлу</h3>
    <div class="input-group">
      <input
        type="file"
        id="topics-file-input"
        accept=".txt,.csv"
        onchange="handleTopicsFileUpload(event)"
      >
      <button class="btn-secondary" onclick="document.getElementById('topics-file-input').click()">
        <i class="bi bi-cloud-upload"></i> Вибрати файл
      </button>
    </div>
    <small style="color: #6b7280; display: block; margin-top: 8px;">
      Формат: TXT (одна тема на рядок) або CSV (колонка "topic")
    </small>
  </div>

  <!-- Topics List -->
  <div class="topics-list-section">
    <h3>📝 Список тем</h3>

    <!-- Filters -->
    <div class="topics-filters">
      <button class="filter-btn active" data-filter="all" onclick="filterTopics('all')">
        <i class="bi bi-list"></i> Всі (<span id="filter-count-all">100</span>)
      </button>
      <button class="filter-btn" data-filter="pending" onclick="filterTopics('pending')">
        <i class="bi bi-hourglass"></i> Очікують (<span id="filter-count-pending">85</span>)
      </button>
      <button class="filter-btn" data-filter="in_progress" onclick="filterTopics('in_progress')">
        <i class="bi bi-arrow-repeat"></i> В роботі (<span id="filter-count-in-progress">0</span>)
      </button>
      <button class="filter-btn" data-filter="completed" onclick="filterTopics('completed')">
        <i class="bi bi-check-circle"></i> Виконано (<span id="filter-count-completed">15</span>)
      </button>
      <button class="filter-btn" data-filter="failed" onclick="filterTopics('failed')">
        <i class="bi bi-x-circle"></i> Помилки (<span id="filter-count-failed">0</span>)
      </button>
    </div>

    <!-- Bulk Actions -->
    <div class="topics-bulk-actions">
      <button class="btn-sm" onclick="clearCompletedTopics()">
        <i class="bi bi-trash"></i> Очистити виконані
      </button>
      <button class="btn-sm" onclick="exportTopics()">
        <i class="bi bi-download"></i> Експортувати список
      </button>
      <button class="btn-sm btn-danger" onclick="clearAllTopics()">
        <i class="bi bi-trash3"></i> Видалити всі
      </button>
    </div>

    <!-- Topics Items (scrollable list) -->
    <div class="topics-items" id="topics-items-list">
      <!-- Empty state -->
      <div class="topics-empty-state" id="topics-empty-state">
        <i class="bi bi-inbox" style="font-size: 48px; color: #d1d5db;"></i>
        <p style="color: #9ca3af;">Немає тем у черзі</p>
        <p style="color: #6b7280; font-size: 14px;">Додайте теми вручну, згенеруйте AI або завантажте з файлу</p>
      </div>

      <!-- Example topic item (template) -->
      <template id="topic-item-template">
        <div class="topic-item" data-topic-id="" data-status="pending">
          <div class="topic-priority-controls">
            <button class="priority-btn" onclick="moveTopic(this, 'up')" title="Пріоритет вище">
              <i class="bi bi-arrow-up"></i>
            </button>
            <button class="priority-btn" onclick="moveTopic(this, 'down')" title="Пріоритет нижче">
              <i class="bi bi-arrow-down"></i>
            </button>
          </div>

          <div class="topic-number">#<span class="number-value">1</span></div>

          <div class="topic-content">
            <div class="topic-text">The Haunted Lighthouse</div>
            <div class="topic-meta">
              <span class="topic-date">Додано: 20.02.2026 14:30</span>
              <span class="topic-content-id" style="display: none;">content_123</span>
            </div>
          </div>

          <div class="topic-status">
            <span class="status-badge status-pending">
              <i class="bi bi-hourglass"></i> Очікує
            </span>
          </div>

          <div class="topic-actions">
            <button class="topic-action-btn" onclick="viewTopicContent(this)" title="Переглянути контент" style="display: none;">
              <i class="bi bi-eye"></i>
            </button>
            <button class="topic-action-btn" onclick="editTopic(this)" title="Редагувати">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="topic-action-btn topic-delete" onclick="deleteTopic(this)" title="Видалити">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- Queue Settings -->
  <div class="queue-settings-section">
    <h3>⚙️ Налаштування черги</h3>

    <div class="form-group">
      <input type="checkbox" id="auto_process_queue" checked>
      <label for="auto_process_queue">Автоматично обробляти чергу (при щоденній генерації)</label>
      <small style="display: block; color: #6b7280; margin-top: 4px;">
        Якщо активно - система автоматично бере наступну тему з черги замість виклику ThemeAgent
      </small>
    </div>

    <div class="form-group">
      <label>Дія після виконання всіх тем:</label>
      <select id="queue_depletion_action">
        <option value="fallback_theme_agent">Fallback to ThemeAgent (викликати ThemeAgent)</option>
        <option value="stop_generation">Stop Generation (зупинити генерацію)</option>
        <option value="regenerate_queue">Regenerate Queue (згенерувати нові теми AI)</option>
      </select>
    </div>
  </div>
</div>
```

---

### **2.2 CSS Styles для Topics Queue**

```css
/* Topics Queue Styles */
.topics-progress {
  margin-bottom: 24px;
}

.progress-bar {
  width: 100%;
  height: 24px;
  background: #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.progress-stats {
  margin-top: 8px;
  text-align: center;
  font-size: 14px;
  color: #6b7280;
}

.progress-percentage {
  margin-left: 8px;
  color: #3b82f6;
  font-weight: 600;
}

/* Add Topic Section */
.add-topic-section,
.generate-topics-section,
.upload-topics-section {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.add-topic-section h3,
.generate-topics-section h3,
.upload-topics-section h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 16px;
  color: #1f2937;
}

.input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-group input[type="text"],
.input-group input[type="number"] {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.btn-ai {
  background: linear-gradient(135deg, #8b5cf6, #3b82f6);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.btn-ai:hover {
  opacity: 0.9;
}

/* Topics Filters */
.topics-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: #f3f4f6;
}

.filter-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* Bulk Actions */
.topics-bulk-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-sm:hover {
  background: #f3f4f6;
}

.btn-danger {
  color: #dc2626;
  border-color: #fecaca;
}

.btn-danger:hover {
  background: #fee2e2;
}

/* Topics Items List */
.topics-items {
  max-height: 600px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
}

.topics-empty-state {
  padding: 60px 20px;
  text-align: center;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  transition: background 0.2s;
}

.topic-item:hover {
  background: #f9fafb;
}

.topic-item:last-child {
  border-bottom: none;
}

/* Priority Controls */
.topic-priority-controls {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.priority-btn {
  background: none;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 2px 6px;
  cursor: pointer;
  color: #6b7280;
  font-size: 12px;
}

.priority-btn:hover {
  background: #f3f4f6;
  color: #3b82f6;
}

/* Topic Number */
.topic-number {
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
  min-width: 40px;
  text-align: right;
}

/* Topic Content */
.topic-content {
  flex: 1;
  min-width: 0;
}

.topic-text {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topic-meta {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
  display: flex;
  gap: 12px;
}

/* Status Badges */
.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.status-pending {
  background: #fef3c7;
  color: #92400e;
}

.status-in-progress {
  background: #dbeafe;
  color: #1e40af;
}

.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-failed {
  background: #fee2e2;
  color: #991b1b;
}

/* Topic Actions */
.topic-actions {
  display: flex;
  gap: 4px;
}

.topic-action-btn {
  background: none;
  border: none;
  padding: 6px;
  cursor: pointer;
  color: #6b7280;
  border-radius: 4px;
  transition: all 0.2s;
}

.topic-action-btn:hover {
  background: #f3f4f6;
  color: #3b82f6;
}

.topic-delete:hover {
  color: #dc2626;
}
```

---

## 3️⃣ DYNAMODB SCHEMA ДЛЯ TOPICS QUEUE

### **Таблиця: `ContentTopicsQueue`**

```json
{
  "TableName": "ContentTopicsQueue",
  "KeySchema": [
    {
      "AttributeName": "channel_id",
      "KeyType": "HASH"  // Partition key
    },
    {
      "AttributeName": "topic_id",
      "KeyType": "RANGE"  // Sort key
    }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "channel_id", "AttributeType": "S" },
    { "AttributeName": "topic_id", "AttributeType": "S" },
    { "AttributeName": "status", "AttributeType": "S" },
    { "AttributeName": "priority", "AttributeType": "N" }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "status-priority-index",
      "KeySchema": [
        { "AttributeName": "channel_id", "KeyType": "HASH" },
        { "AttributeName": "status", "KeyType": "RANGE" }
      ],
      "Projection": { "ProjectionType": "ALL" }
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### **Структура запису:**

```json
{
  "channel_id": "UCxxx",  // Partition key
  "topic_id": "20260220143000_001",  // Sort key (timestamp + serial)

  "topic_text": "The Haunted Lighthouse of Lost Souls",

  "status": "pending",  // pending | in_progress | completed | failed
  "priority": 100,  // Для сортування (вище число = вищий пріоритет)

  "created_at": "2026-02-20T14:30:00Z",
  "started_at": null,  // Timestamp коли почалась генерація
  "completed_at": null,  // Timestamp коли завершилась генерація

  "content_id": null,  // ID згенерованого контенту (коли completed)
  "error_message": null,  // Повідомлення про помилку (якщо failed)

  "source": "manual",  // manual | ai_generated | file_upload
  "user_id": "user_123"  // Для multi-tenant isolation
}
```

---

## 4️⃣ LAMBDA FUNCTIONS ДЛЯ TOPICS QUEUE

### **4.1 content-topics-add** (нова Lambda)

**Призначення:** Додати тему в чергу (вручну)

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "user_id": "user_123",
  "topic_text": "The Haunted Lighthouse",
  "priority": 100  // Optional, default 100
}
```

**Вихід:**
```json
{
  "success": true,
  "topic_id": "20260220143000_001",
  "message": "Topic added to queue"
}
```

**Код (Python):**
```python
import boto3
import json
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ContentTopicsQueue')

def lambda_handler(event, context):
    channel_id = event['channel_id']
    user_id = event['user_id']
    topic_text = event['topic_text'].strip()
    priority = event.get('priority', 100)

    # Generate topic_id (timestamp + serial)
    topic_id = datetime.utcnow().strftime('%Y%m%d%H%M%S') + '_' + str(int(datetime.utcnow().timestamp() * 1000) % 1000).zfill(3)

    # Add to DynamoDB
    table.put_item(
        Item={
            'channel_id': channel_id,
            'topic_id': topic_id,
            'topic_text': topic_text,
            'status': 'pending',
            'priority': Decimal(str(priority)),
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'started_at': None,
            'completed_at': None,
            'content_id': None,
            'error_message': None,
            'source': 'manual',
            'user_id': user_id
        }
    )

    return {
        'success': True,
        'topic_id': topic_id,
        'message': 'Topic added to queue'
    }
```

---

### **4.2 content-topics-generate** (нова Lambda)

**Призначення:** Згенерувати теми за допомогою AI (OpenAI)

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "user_id": "user_123",
  "count": 20,  // Кількість тем для генерації
  "context": "horror stories about abandoned places"  // Optional
}
```

**Вихід:**
```json
{
  "success": true,
  "generated_count": 20,
  "topics": [
    { "topic_id": "...", "topic_text": "The Abandoned Asylum" },
    { "topic_id": "...", "topic_text": "The Forgotten Cemetery" }
  ]
}
```

**Prompt для OpenAI:**
```
You are a creative topic generator for a YouTube channel.

Channel Info:
- Genre: {genre}
- Tone: {tone}
- World Type: {world_type}
- Story Mode: {story_mode}

Generate {count} unique, engaging topics for this channel.

Requirements:
- Each topic should be 5-15 words
- Topics must be unique and varied
- Follow the channel's tone and genre
- Avoid clichés
- Format: JSON array of strings

Example output:
["The Haunted Lighthouse of Lost Souls", "Whispers from the Forgotten Well", ...]
```

---

### **4.3 content-topics-upload** (нова Lambda)

**Призначення:** Завантажити теми з файлу (TXT/CSV)

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "user_id": "user_123",
  "file_content": "The Haunted House\nThe Dark Forest\nThe Cursed Mirror",
  "file_type": "txt"  // txt | csv
}
```

**Логіка:**
- Parse файл (TXT: split by newline, CSV: extract 'topic' column)
- Validate кожну тему (не пусто, <= 200 символів)
- Add кожну тему в DynamoDB
- Limit: максимум 100 тем на канал (перевірити перед додаванням)

---

### **4.4 content-topics-list** (нова Lambda)

**Призначення:** Отримати список тем для каналу

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "user_id": "user_123",
  "status": "all"  // all | pending | in_progress | completed | failed
}
```

**Вихід:**
```json
{
  "success": true,
  "topics": [
    {
      "topic_id": "20260220143000_001",
      "topic_text": "The Haunted Lighthouse",
      "status": "pending",
      "priority": 100,
      "created_at": "2026-02-20T14:30:00Z"
    }
  ],
  "total_count": 100,
  "counts_by_status": {
    "pending": 85,
    "in_progress": 0,
    "completed": 15,
    "failed": 0
  }
}
```

---

### **4.5 content-topics-delete** (нова Lambda)

**Призначення:** Видалити тему з черги

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "user_id": "user_123",
  "topic_id": "20260220143000_001"
}
```

---

### **4.6 content-topics-update-status** (нова Lambda)

**Призначення:** Оновити статус теми (викликається автоматично Step Functions)

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "topic_id": "20260220143000_001",
  "status": "in_progress",  // in_progress | completed | failed
  "content_id": "content_123",  // Optional (when completed)
  "error_message": "OpenAI API error"  // Optional (when failed)
}
```

---

### **4.7 content-topics-get-next** (нова Lambda)

**Призначення:** Отримати наступну pending тему з черги (для Step Functions)

**Вхід:**
```json
{
  "channel_id": "UCxxx",
  "user_id": "user_123"
}
```

**Вихід:**
```json
{
  "success": true,
  "has_topic": true,
  "topic": {
    "topic_id": "20260220143000_001",
    "topic_text": "The Haunted Lighthouse",
    "priority": 100
  }
}
```

**Логіка:**
- Query DynamoDB: channel_id + status=pending
- Sort by priority DESC, created_at ASC
- Return перша тема
- Якщо немає pending тем → `has_topic: false`

---

## 5️⃣ JAVASCRIPT FUNCTIONS (channels-unified.js)

```javascript
// ==========================================
// TOPICS QUEUE MANAGEMENT FUNCTIONS
// ==========================================

/**
 * Add topic manually
 */
async function addTopicManually() {
  const input = document.getElementById('manual-topic-input');
  const topicText = input.value.trim();

  if (!topicText) {
    alert('⚠️ Введіть текст теми');
    return;
  }

  if (topicText.length > 200) {
    alert('⚠️ Тема занадто довга (максимум 200 символів)');
    return;
  }

  try {
    const response = await fetch('TOPICS_API_URL/add', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authManager.getAuthHeaders()
      },
      body: JSON.stringify({
        channel_id: selectedChannelId,
        user_id: authManager.getUserId(),
        topic_text: topicText
      })
    });

    const result = await response.json();

    if (result.success) {
      showNotification('✅ Тему додано!', 'success');
      input.value = '';
      loadTopicsList();  // Reload list
    } else {
      throw new Error(result.error || 'Failed to add topic');
    }
  } catch (error) {
    console.error('Error adding topic:', error);
    showNotification('❌ Помилка: ' + error.message, 'danger');
  }
}

/**
 * Generate topics with AI
 */
async function generateTopicsWithAI() {
  const count = parseInt(document.getElementById('generate-topics-count').value);
  const context = document.getElementById('generate-topics-context').value.trim();

  if (count < 1 || count > 100) {
    alert('⚠️ Кількість тем має бути від 1 до 100');
    return;
  }

  // Show loading state
  const btn = event.target;
  const originalHTML = btn.innerHTML;
  btn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Генерую...';
  btn.disabled = true;

  try {
    const response = await fetch('TOPICS_API_URL/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authManager.getAuthHeaders()
      },
      body: JSON.stringify({
        channel_id: selectedChannelId,
        user_id: authManager.getUserId(),
        count: count,
        context: context || null
      })
    });

    const result = await response.json();

    if (result.success) {
      showNotification(`✅ Згенеровано ${result.generated_count} тем!`, 'success');
      loadTopicsList();
    } else {
      throw new Error(result.error || 'Failed to generate topics');
    }
  } catch (error) {
    console.error('Error generating topics:', error);
    showNotification('❌ Помилка: ' + error.message, 'danger');
  } finally {
    btn.innerHTML = originalHTML;
    btn.disabled = false;
  }
}

/**
 * Handle file upload
 */
async function handleTopicsFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const fileType = file.name.endsWith('.csv') ? 'csv' : 'txt';

  const reader = new FileReader();
  reader.onload = async (e) => {
    const fileContent = e.target.result;

    try {
      const response = await fetch('TOPICS_API_URL/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authManager.getAuthHeaders()
        },
        body: JSON.stringify({
          channel_id: selectedChannelId,
          user_id: authManager.getUserId(),
          file_content: fileContent,
          file_type: fileType
        })
      });

      const result = await response.json();

      if (result.success) {
        showNotification(`✅ Завантажено ${result.added_count} тем!`, 'success');
        loadTopicsList();
      } else {
        throw new Error(result.error || 'Failed to upload topics');
      }
    } catch (error) {
      console.error('Error uploading topics:', error);
      showNotification('❌ Помилка: ' + error.message, 'danger');
    }
  };

  reader.readAsText(file);
}

/**
 * Load topics list
 */
async function loadTopicsList(statusFilter = 'all') {
  try {
    const response = await fetch('TOPICS_API_URL/list', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authManager.getAuthHeaders()
      },
      body: JSON.stringify({
        channel_id: selectedChannelId,
        user_id: authManager.getUserId(),
        status: statusFilter
      })
    });

    const result = await response.json();

    if (result.success) {
      renderTopicsList(result.topics);
      updateTopicsStats(result.total_count, result.counts_by_status);
    }
  } catch (error) {
    console.error('Error loading topics:', error);
  }
}

/**
 * Render topics list
 */
function renderTopicsList(topics) {
  const container = document.getElementById('topics-items-list');
  const emptyState = document.getElementById('topics-empty-state');
  const template = document.getElementById('topic-item-template');

  // Clear list
  container.innerHTML = '';

  if (topics.length === 0) {
    emptyState.style.display = 'block';
    return;
  }

  emptyState.style.display = 'none';

  topics.forEach((topic, index) => {
    const clone = template.content.cloneNode(true);

    const item = clone.querySelector('.topic-item');
    item.dataset.topicId = topic.topic_id;
    item.dataset.status = topic.status;

    clone.querySelector('.number-value').textContent = index + 1;
    clone.querySelector('.topic-text').textContent = topic.topic_text;
    clone.querySelector('.topic-date').textContent = 'Додано: ' + formatDate(topic.created_at);

    // Status badge
    const statusBadge = clone.querySelector('.status-badge');
    statusBadge.className = 'status-badge status-' + topic.status;

    const statusIcons = {
      'pending': 'hourglass',
      'in_progress': 'arrow-repeat',
      'completed': 'check-circle',
      'failed': 'x-circle'
    };

    const statusLabels = {
      'pending': 'Очікує',
      'in_progress': 'В роботі',
      'completed': 'Виконано',
      'failed': 'Помилка'
    };

    statusBadge.innerHTML = `<i class="bi bi-${statusIcons[topic.status]}"></i> ${statusLabels[topic.status]}`;

    // Show view button only if completed
    if (topic.status === 'completed' && topic.content_id) {
      clone.querySelector('.topic-content-id').textContent = topic.content_id;
      clone.querySelector('.topic-action-btn[onclick*="viewTopicContent"]').style.display = 'inline-block';
    }

    container.appendChild(clone);
  });
}

/**
 * Update topics statistics
 */
function updateTopicsStats(totalCount, countsByStatus) {
  document.getElementById('topics-total-count').textContent = totalCount;
  document.getElementById('topics-completed-count').textContent = countsByStatus.completed || 0;

  const percentage = totalCount > 0 ? Math.round((countsByStatus.completed / totalCount) * 100) : 0;
  document.getElementById('topics-progress-fill').style.width = percentage + '%';
  document.querySelector('.progress-percentage').textContent = '(' + percentage + '%)';

  // Update filter counts
  document.getElementById('filter-count-all').textContent = totalCount;
  document.getElementById('filter-count-pending').textContent = countsByStatus.pending || 0;
  document.getElementById('filter-count-in-progress').textContent = countsByStatus.in_progress || 0;
  document.getElementById('filter-count-completed').textContent = countsByStatus.completed || 0;
  document.getElementById('filter-count-failed').textContent = countsByStatus.failed || 0;
}

/**
 * Filter topics by status
 */
function filterTopics(status) {
  // Update filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === status);
  });

  // Reload list
  loadTopicsList(status);
}

/**
 * Delete topic
 */
async function deleteTopic(btn) {
  const item = btn.closest('.topic-item');
  const topicId = item.dataset.topicId;
  const topicText = item.querySelector('.topic-text').textContent;

  if (!confirm(`Видалити тему "${topicText}"?`)) {
    return;
  }

  try {
    const response = await fetch('TOPICS_API_URL/delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authManager.getAuthHeaders()
      },
      body: JSON.stringify({
        channel_id: selectedChannelId,
        user_id: authManager.getUserId(),
        topic_id: topicId
      })
    });

    const result = await response.json();

    if (result.success) {
      showNotification('✅ Тему видалено', 'success');
      loadTopicsList();
    } else {
      throw new Error(result.error || 'Failed to delete topic');
    }
  } catch (error) {
    console.error('Error deleting topic:', error);
    showNotification('❌ Помилка: ' + error.message, 'danger');
  }
}

/**
 * Move topic priority (up/down)
 */
async function moveTopic(btn, direction) {
  const item = btn.closest('.topic-item');
  const topicId = item.dataset.topicId;

  // TODO: Implement priority update API call
  console.log('Move topic', topicId, direction);
}

/**
 * View topic content (for completed topics)
 */
function viewTopicContent(btn) {
  const item = btn.closest('.topic-item');
  const contentId = item.querySelector('.topic-content-id').textContent;

  // Redirect to content page
  window.location.href = `content.html?content_id=${contentId}`;
}

/**
 * Edit topic
 */
function editTopic(btn) {
  const item = btn.closest('.topic-item');
  const topicText = item.querySelector('.topic-text').textContent;

  const newText = prompt('Редагувати тему:', topicText);
  if (newText && newText.trim() && newText.trim() !== topicText) {
    // TODO: Implement topic edit API call
    console.log('Edit topic:', newText);
  }
}

/**
 * Clear completed topics
 */
async function clearCompletedTopics() {
  if (!confirm('Видалити всі виконані теми?')) {
    return;
  }

  // TODO: Implement bulk delete API call
  console.log('Clear completed topics');
}

/**
 * Clear all topics
 */
async function clearAllTopics() {
  if (!confirm('⚠️ УВАГА! Видалити ВСІ теми з черги? Цю дію не можна відмінити!')) {
    return;
  }

  // TODO: Implement bulk delete all API call
  console.log('Clear all topics');
}

/**
 * Export topics to file
 */
function exportTopics() {
  // TODO: Implement export functionality (CSV/TXT)
  console.log('Export topics');
}

/**
 * Format date helper
 */
function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString('uk-UA') + ' ' + date.toLocaleTimeString('uk-UA');
}
```

---

## 6️⃣ INTEGRATION З STEP FUNCTIONS

### **Модифікація Phase 1 - ThemeAgent замінюється на Topics Queue**

```json
{
  "QueryTitles": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "content-query-titles",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "config_id.$": "$.config_id",
        "channel_name.$": "$.channel_name",
        "genre.$": "$.genre"
      }
    },
    "ResultPath": "$.queryResult",
    "Next": "CheckAutoProcessQueue"
  },

  "CheckAutoProcessQueue": {
    "Type": "Choice",
    "Comment": "Check if channel has auto_process_queue enabled",
    "Choices": [
      {
        "Variable": "$.auto_process_queue",
        "BooleanEquals": true,
        "Next": "GetNextTopicFromQueue"
      }
    ],
    "Default": "ThemeAgent"
  },

  "GetNextTopicFromQueue": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Comment": "Get next pending topic from queue",
    "Parameters": {
      "FunctionName": "content-topics-get-next",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "user_id.$": "$.user_id"
      }
    },
    "ResultPath": "$.topicQueueResult",
    "Next": "CheckIfTopicAvailable"
  },

  "CheckIfTopicAvailable": {
    "Type": "Choice",
    "Comment": "If queue has topic, use it. Otherwise fallback to ThemeAgent.",
    "Choices": [
      {
        "Variable": "$.topicQueueResult.Payload.has_topic",
        "BooleanEquals": true,
        "Next": "MarkTopicInProgress"
      }
    ],
    "Default": "HandleQueueDepletion"
  },

  "MarkTopicInProgress": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Comment": "Mark topic as in_progress",
    "Parameters": {
      "FunctionName": "content-topics-update-status",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "topic_id.$": "$.topicQueueResult.Payload.topic.topic_id",
        "status": "in_progress"
      }
    },
    "ResultPath": "$.topicUpdateResult",
    "Next": "UseTopicFromQueue"
  },

  "UseTopicFromQueue": {
    "Type": "Pass",
    "Comment": "Use topic from queue as selected_topic",
    "Parameters": {
      "channel_id.$": "$.channel_id",
      "user_id.$": "$.user_id",
      "selected_topic.$": "$.topicQueueResult.Payload.topic.topic_text",
      "topic_id.$": "$.topicQueueResult.Payload.topic.topic_id",
      "from_queue": true
    },
    "ResultPath": "$.themeResult",
    "Next": "CheckFactualMode"
  },

  "HandleQueueDepletion": {
    "Type": "Choice",
    "Comment": "What to do when queue is empty?",
    "Choices": [
      {
        "Variable": "$.queue_depletion_action",
        "StringEquals": "fallback_theme_agent",
        "Next": "ThemeAgent"
      },
      {
        "Variable": "$.queue_depletion_action",
        "StringEquals": "regenerate_queue",
        "Next": "RegenerateQueue"
      }
    ],
    "Default": "StopGeneration"
  },

  "RegenerateQueue": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Comment": "Auto-generate new topics when queue depleted",
    "Parameters": {
      "FunctionName": "content-topics-generate",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "user_id.$": "$.user_id",
        "count": 50
      }
    },
    "ResultPath": "$.regenerateResult",
    "Next": "GetNextTopicFromQueue"
  },

  "StopGeneration": {
    "Type": "Fail",
    "Error": "QueueDepleted",
    "Cause": "Topic queue is empty and queue_depletion_action is set to stop_generation"
  },

  "ThemeAgent": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Comment": "Fallback to ThemeAgent if queue disabled or empty",
    "Parameters": {
      "FunctionName": "content-theme-agent",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "genre.$": "$.genre",
        "titles.$": "$.queryResult.data.titles"
      }
    },
    "ResultPath": "$.themeResult",
    "Next": "CheckFactualMode"
  }
}
```

### **Після завершення генерації - оновити статус теми:**

Додати в кінець Phase 3 (після SaveFinalContent):

```json
{
  "UpdateTopicStatus": {
    "Type": "Choice",
    "Comment": "If topic was from queue, update status to completed",
    "Choices": [
      {
        "Variable": "$.themeResult.from_queue",
        "BooleanEquals": true,
        "Next": "MarkTopicCompleted"
      }
    ],
    "Default": "VideoAssemblyComplete"
  },

  "MarkTopicCompleted": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "content-topics-update-status",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "topic_id.$": "$.themeResult.topic_id",
        "status": "completed",
        "content_id.$": "$.narrativeResult.data.narrative_id"
      }
    },
    "End": true
  },

  "VideoAssemblyComplete": {
    "Type": "Pass",
    "End": true
  }
}
```

---

## 📋 MIGRATION CHECKLIST

### **Phase 1: UI Extended (2-3 дні)**
- [ ] Замінити всі текстові поля на comprehensive dropdowns
- [ ] Додати Topics Queue Manager секцію
- [ ] Додати CSS styles для Topics Queue
- [ ] Додати JavaScript functions для Topics Queue
- [ ] Тестування UI

### **Phase 2: DynamoDB (1 день)**
- [ ] Створити таблицю `ContentTopicsQueue`
- [ ] Додати GSI для status-priority lookups
- [ ] Тестування схеми

### **Phase 3: Lambda Functions (1 тиждень)**
- [ ] `content-topics-add`
- [ ] `content-topics-generate`
- [ ] `content-topics-upload`
- [ ] `content-topics-list`
- [ ] `content-topics-delete`
- [ ] `content-topics-update-status`
- [ ] `content-topics-get-next`
- [ ] Тестування всіх Lambda

### **Phase 4: Step Functions Integration (2 дні)**
- [ ] Додати CheckAutoProcessQueue state
- [ ] Додати GetNextTopicFromQueue state
- [ ] Додати HandleQueueDepletion logic
- [ ] Додати UpdateTopicStatus після завершення
- [ ] Тестування integration

### **Phase 5: Testing (3 дні)**
- [ ] Тестування manual add topic
- [ ] Тестування AI generate topics
- [ ] Тестування file upload
- [ ] Тестування queue processing
- [ ] Тестування fallback to ThemeAgent

### **Phase 6: Deployment (1 день)**
- [ ] Deploy всіх Lambda
- [ ] Update Step Functions
- [ ] Update UI
- [ ] Rollback plan

**Total:** ~2-3 тижні

---

## ✅ ПЕРЕВАГИ НОВОЇ СИСТЕМИ

### **Story Engine:**
- ✅ **Більше контролю** - comprehensive dropdowns замість текстових полів
- ✅ **Більше опцій** - сотні готових варіантів для кожного параметра
- ✅ **Менше помилок** - користувач не може ввести невалідне значення
- ✅ **Кращий UX** - не треба згадувати назви архетипів, тонів, структур

### **Topics Queue:**
- ✅ **Планування контенту** - можна завантажити 100 тем наперед
- ✅ **Автоматизація** - система сама бере теми з черги
- ✅ **Контроль** - бачимо статус кожної теми
- ✅ **Гнучкість** - AI-генерація, manual, file upload
- ✅ **Масштабування** - легко згенерувати контент на місяць вперед

---

**ГОТОВО! 🎉**
