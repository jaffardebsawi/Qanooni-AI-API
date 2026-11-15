"""Built-in templates.

Body markup (plain text):
  # Title              document title
  ### Heading          unnumbered heading (Parties, Background, ...)
  ## Heading           numbered clause heading (numbered automatically)
  - text               numbered sub-clause (1.1, 1.2, ... automatic)
  * text               lettered item (a), (b), ... under the previous sub-clause
  @sign {{party}}      signature block for a party
  {{key}}              field placeholder
  {{#key}}...{{/key}}  block included only when the field has a value
"""

NDA_BODY = """# MUTUAL CONFIDENTIALITY AGREEMENT
Effective date: {{effective_date}}
### Parties
1. {{party_a_name}} ({{party_a_short}}); and
2. {{party_b_name}} ({{party_b_short}}),
each a Party and together the Parties.
### Background
A. The Parties wish to evaluate a potential relationship concerning {{purpose}}.
B. In connection with that evaluation, each Party may disclose Confidential Information to the other.
C. The Parties agree to protect and restrict the use of that Confidential Information on the terms of this Agreement.
### Agreed terms
## Definitions and interpretation
- Definitions. In this Agreement:
Affiliate means, in relation to a Party, any undertaking that is from time to time its holding company, its subsidiary, a subsidiary of its holding company, or otherwise under common control with it.
Business Day means a day other than a Saturday, Sunday or public holiday on which banks in the place of governing law are open for general commercial business.
Confidential Information means all information of a confidential or commercially sensitive nature that is disclosed or made available, directly or indirectly, by or on behalf of a Disclosing Party to a Recipient during the Term, whether disclosed orally, visually, electronically, in writing or in any other form, including:
* information relating to the Disclosing Party or any of its Affiliates, customers, suppliers, business partners or personnel;
* business plans, strategies, pricing, forecasts, financial information and contractual arrangements;
* technical information, software, designs, specifications, know-how and research;
* personal data and customer data;
* the existence, status and content of the Parties' discussions and the existence and terms of this Agreement; and
* all analyses, notes, summaries and other materials that contain or are derived from any of the above,
whether or not marked as confidential, provided that it is confidential by its nature or would reasonably be understood to be confidential.
Disclosing Party means the Party that discloses or makes available Confidential Information, or on whose behalf it is disclosed.
Purpose means evaluating, discussing and, if the Parties agree, pursuing a potential relationship concerning {{purpose}}.
Recipient means the Party that receives Confidential Information, directly or through its Representatives.
Representatives means, in relation to a Party, its employees, directors, Affiliates, professional advisers, insurers and contractors, in each case only where the person requires access to Confidential Information for the Purpose.
- Interpretation. References to legislation include that legislation as amended or re-enacted. The words "including" and "include" are illustrative. Headings do not affect interpretation.
## Term
- This Agreement commences on the Effective Date and continues for {{term_years}} year(s), unless terminated earlier by either Party on written notice.
- Confidential Information may be disclosed throughout the Term.
- Neither Party is obliged to disclose any information, continue discussions or enter into any further agreement.
## Excluded information
- Confidential Information does not include information that the Recipient can establish:
* was lawfully in its possession without restriction before it was disclosed;
* is or becomes publicly available other than through a breach of this Agreement;
* is lawfully received from a third party that is not under a duty of confidence;
* is independently developed without use of the Confidential Information; or
* the Disclosing Party confirms in writing may be used or disclosed without restriction.
- The burden of proving that an exclusion applies rests with the Recipient.
## Confidentiality and restricted use
- The Recipient must:
* keep the Disclosing Party's Confidential Information strictly confidential;
* use it solely for the Purpose and for no other purpose;
* not disclose it except as expressly permitted by this Agreement;
* protect it with at least the same degree of care it uses for its own confidential information, and no less than reasonable care; and
* promptly notify the Disclosing Party on becoming aware of any actual or suspected unauthorised access, use or disclosure.
## Disclosure to Representatives
- The Recipient may disclose Confidential Information only to Representatives who need it for the Purpose, are informed of its confidential nature, and are bound by obligations no less protective than this Agreement.
- The Recipient is liable for any act or omission of its Representatives that would breach this Agreement if committed by the Recipient.
{{#deliverables}}## Deliverables
- In connection with the Purpose, the Parties will provide the following deliverables: {{deliverables}}.
- Each deliverable, and all Confidential Information contained in it, is Confidential Information of the Party that provides it.
- Delivery of a deliverable does not transfer ownership of, or grant any licence to, any intellectual property rights in it.
{{/deliverables}}## Personal data
- Each Party must comply with applicable data protection law in relation to any personal data disclosed under this Agreement. Personal data must be shared only where necessary for the Purpose and, where required by law, under separate data protection terms.
## Intellectual property and no licence
- All Confidential Information remains the property of the Disclosing Party. Nothing in this Agreement grants the Recipient any licence or right in respect of the Disclosing Party's intellectual property rights.
## Required disclosure
- The Recipient may disclose Confidential Information to the extent required by law, court order or a regulatory authority, provided that, where lawful, it gives the Disclosing Party prompt prior notice, discloses only the minimum required, and cooperates with any effort to limit the disclosure.
## Return and destruction
- On written request, and in any event on termination, the Recipient must promptly return or securely destroy the Disclosing Party's Confidential Information and confirm in writing that it has done so.
- The Recipient may retain copies where required by law or held in routine, inaccessible automatic back-ups, provided they remain subject to this Agreement.
## No warranty
- Confidential Information is provided without warranty of any kind as to accuracy or completeness, and neither Party has any liability for its use except as set out in a separate written agreement.
## Remedies
- Each Party acknowledges that damages alone may not be an adequate remedy for breach of this Agreement and that the Disclosing Party is entitled to seek injunctive relief or specific performance in addition to any other remedy.
## Duration of obligations
- The obligations in this Agreement continue for {{survival_years}} year(s) after the end of the Term, and for as long as any Confidential Information remains a trade secret.
## No partnership or agency
- Nothing in this Agreement creates a partnership, joint venture, agency or employment relationship between the Parties.
## Assignment
- Neither Party may assign or transfer any of its rights or obligations under this Agreement without the prior written consent of the other Party.
## Notices
- A notice under this Agreement must be in writing and delivered to the other Party's registered office or to another address that the Party has notified in writing.
## Entire agreement, variation and waiver
- This Agreement is the entire agreement between the Parties about its subject matter.
- No variation of this Agreement is effective unless it is in writing and signed by both Parties.
- A failure or delay in exercising a right is not a waiver of that right.
## Severance
- If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions continue in full force.
## Third-party rights
- A person who is not a Party has no right to enforce any term of this Agreement.
## Counterparts and electronic signature
- This Agreement may be executed in counterparts and signed using a reliable electronic-signature method by authorised signatories.
## Governing law
- This Agreement and any dispute or non-contractual obligation arising out of or in connection with it are governed by the laws of {{governing_law}}.
## Jurisdiction
- The courts of {{governing_law}} have exclusive jurisdiction to settle any dispute or claim arising out of or in connection with this Agreement, its subject matter or formation.
### Execution
This Agreement is entered into and takes effect on the Effective Date.
@sign {{party_a_name}}
@sign {{party_b_name}}
"""

SERVICE_BODY = """# SERVICES AGREEMENT
Effective date: {{effective_date}}
### Parties
1. {{supplier_name}} ({{supplier_short}}); and
2. {{client_name}} ({{client_short}}).
### Agreed terms
## Services
- The Supplier will provide the following services to the Client: {{services}}.
- The Supplier will perform the services with reasonable skill and care and in accordance with applicable law.
## Fees and payment
- The Client will pay the Supplier {{fees}}.
- The Supplier will invoice the Client, and the Client will pay each undisputed invoice within {{payment_days}} days of receipt.
## Term and termination
- This Agreement starts on the Effective Date and continues for {{term_months}} month(s), unless terminated earlier under this clause.
- Either Party may terminate this Agreement immediately by written notice if the other Party commits a material breach that is not remedied within 30 days of notice requiring it to be remedied.
## Confidentiality
- Each Party must keep confidential all non-public information of the other Party that it receives in connection with this Agreement, and use it only to perform or receive the services.
## Intellectual property
- Each Party retains ownership of its pre-existing intellectual property. Ownership of materials created specifically for the Client under this Agreement passes to the Client on payment in full.
## Liability
- Nothing in this Agreement limits liability that cannot be limited by law.
- Subject to the previous sub-clause, the Supplier's total liability under this Agreement is limited to the fees paid or payable under it.
## General
- This Agreement is the entire agreement between the Parties about its subject matter.
- No variation is effective unless it is in writing and signed by both Parties.
- Neither Party may assign this Agreement without the prior written consent of the other.
## Governing law and jurisdiction
- This Agreement and any dispute arising out of or in connection with it are governed by the laws of {{governing_law}}, and the courts of {{governing_law}} have exclusive jurisdiction.
### Execution
This Agreement is entered into and takes effect on the Effective Date.
@sign {{supplier_name}}
@sign {{client_name}}
"""


NDA_AR_BODY = """# اتفاقية سرية متبادلة
تاريخ السريان: {{effective_date}}
### الأطراف
1. {{party_a_name}} («الطرف الأول»)؛ و
2. {{party_b_name}} («الطرف الثاني»)،
ويشار إليهما معاً بـ«الطرفين» وإلى كل منهما بـ«الطرف».
### تمهيد
أ. يرغب الطرفان في دراسة علاقة محتملة بينهما بشأن {{purpose}}.
ب. وفي سياق هذه الدراسة، قد يفصح كل طرف للآخر عن معلومات سرية.
ج. ويتفق الطرفان على حماية تلك المعلومات السرية وحصر استخدامها وفق أحكام هذه الاتفاقية.
### الشروط المتفق عليها
## التعريفات والتفسير
- التعريفات. في هذه الاتفاقية يكون للكلمات والعبارات التالية المعاني المبينة قرينها:
الشركة التابعة: أي منشأة تتبع الطرف أو تسيطر عليه أو تخضع معه لسيطرة مشتركة.
المعلومات السرية: جميع المعلومات ذات الطبيعة السرية أو الحساسة تجارياً التي يفصح عنها الطرف المفصح للطرف المتلقي أو يتيحها له، بصورة مباشرة أو غير مباشرة، خلال مدة الاتفاقية، سواء كانت شفهية أو مرئية أو إلكترونية أو مكتوبة أو بأي شكل آخر، بما في ذلك:
* المعلومات المتعلقة بالطرف المفصح أو بشركاته التابعة أو عملائه أو مورديه أو شركائه أو موظفيه؛
* الخطط التجارية والاستراتيجيات والتسعير والتوقعات والمعلومات المالية والترتيبات التعاقدية؛
* المعلومات الفنية والبرمجيات والتصاميم والمواصفات والمعرفة الفنية والأبحاث؛
* البيانات الشخصية وبيانات العملاء؛
* وجود المباحثات بين الطرفين وحالتها ومضمونها، ووجود هذه الاتفاقية وشروطها؛
* جميع التحليلات والملاحظات والملخصات وغيرها من المواد التي تتضمن أياً مما سبق أو تُستمد منه،
سواء وُضعت عليها علامة السرية أم لا، متى كانت سرية بطبيعتها أو يُتوقع بصورة معقولة أن تُعد كذلك.
الطرف المفصح: الطرف الذي يفصح عن المعلومات السرية أو يتيحها، أو الذي يُفصح عنها نيابة عنه.
الغرض: تقييم ومناقشة، وعند اتفاق الطرفين متابعة، علاقة محتملة بشأن {{purpose}}.
الطرف المتلقي: الطرف الذي يتلقى المعلومات السرية، مباشرة أو عن طريق ممثليه.
الممثلون: موظفو الطرف ومديروه وشركاته التابعة ومستشاروه المهنيون ومؤمّنوه ومتعاقدوه، وذلك فقط متى احتاج أي منهم إلى الاطلاع على المعلومات السرية لأجل الغرض.
- التفسير. تشمل الإشارة إلى أي تشريع ذلك التشريع بصيغته المعدلة أو المعاد إصدارها. وعبارة «بما في ذلك» للتمثيل لا للحصر. ولا تؤثر العناوين في تفسير الاتفاقية.
## المدة
- تسري هذه الاتفاقية من تاريخ السريان وتستمر لمدة {{term_years}} سنة (سنوات)، ما لم ينهها أي من الطرفين قبل ذلك بإشعار كتابي.
- يجوز الإفصاح عن المعلومات السرية طوال مدة الاتفاقية.
- لا يلتزم أي من الطرفين بالإفصاح عن أي معلومات أو بمواصلة المباحثات أو بإبرام أي اتفاق آخر.
## المعلومات المستثناة
- لا تشمل المعلومات السرية أي معلومات يستطيع الطرف المتلقي إثبات أنها:
* كانت في حوزته بصورة مشروعة ودون قيد قبل الإفصاح عنها؛
* أصبحت متاحة للعموم بغير طريق الإخلال بهذه الاتفاقية؛
* وردته بصورة مشروعة من طرف ثالث غير ملزم بالسرية؛
* جرى تطويرها بصورة مستقلة دون استخدام المعلومات السرية؛ أو
* أكد الطرف المفصح كتابةً جواز استخدامها أو الإفصاح عنها دون قيد.
- يقع عبء إثبات انطباق أي استثناء على الطرف المتلقي.
## السرية وحصر الاستخدام
- يلتزم الطرف المتلقي بما يلي:
* المحافظة على سرية المعلومات السرية للطرف المفصح بصرامة؛
* استخدامها لأجل الغرض وحده ودون أي غرض آخر؛
* عدم الإفصاح عنها إلا بالقدر المسموح به صراحةً في هذه الاتفاقية؛
* حمايتها بدرجة من العناية لا تقل عن تلك التي يحمي بها معلوماته السرية، وبما لا يقل عن العناية المعقولة؛
* إخطار الطرف المفصح فوراً عند علمه بأي وصول أو استخدام أو إفصاح غير مصرح به، فعلي أو محتمل.
## الإفصاح للممثلين
- يجوز للطرف المتلقي الإفصاح عن المعلومات السرية فقط للممثلين الذين يحتاجون إليها لأجل الغرض، وبعد إحاطتهم بطبيعتها السرية وإلزامهم بالتزامات لا تقل حماية عن التزامات هذه الاتفاقية.
- يكون الطرف المتلقي مسؤولاً عن أي فعل أو امتناع صادر عن ممثليه يُعد إخلالاً بهذه الاتفاقية لو صدر عنه.
{{#deliverables}}## المخرجات
- تتصل بالغرض المخرجات التالية التي سيقدمها الطرفان: {{deliverables}}.
- تُعد كل مخرجات، وكل ما تتضمنه من معلومات سرية، معلومات سرية للطرف الذي يقدمها.
- لا يؤدي تسليم أي مخرجات إلى نقل ملكية حقوق الملكية الفكرية فيها ولا إلى منح ترخيص بها.
{{/deliverables}}## البيانات الشخصية
- يلتزم كل طرف بالامتثال لقوانين حماية البيانات المعمول بها فيما يتعلق بأي بيانات شخصية يُفصح عنها بموجب هذه الاتفاقية. ولا تُشارَك البيانات الشخصية إلا عند الضرورة لأجل الغرض، وبموجب شروط مستقلة لحماية البيانات حيثما يقتضي القانون ذلك.
## الملكية الفكرية وعدم الترخيص
- تظل جميع المعلومات السرية ملكاً للطرف المفصح. ولا تمنح هذه الاتفاقية الطرف المتلقي أي ترخيص أو حق فيما يتعلق بحقوق الملكية الفكرية للطرف المفصح.
## الإفصاح المطلوب نظاماً
- يجوز للطرف المتلقي الإفصاح عن المعلومات السرية بالقدر الذي يقتضيه القانون أو أمر قضائي أو جهة تنظيمية، على أن يُخطر الطرف المفصح مسبقاً وبصورة عاجلة حيثما كان ذلك جائزاً، وأن يقتصر على الحد الأدنى المطلوب، وأن يتعاون في أي مسعى للحد من الإفصاح.
## الإعادة والإتلاف
- يلتزم الطرف المتلقي، بناءً على طلب كتابي، وفي جميع الأحوال عند انتهاء الاتفاقية، بإعادة المعلومات السرية للطرف المفصح أو إتلافها بصورة آمنة، وبأن يؤكد ذلك كتابةً.
- يجوز للطرف المتلقي الاحتفاظ بنسخ حيثما يقتضي القانون ذلك أو كانت محفوظة في نسخ احتياطية تلقائية معتادة لا يمكن الوصول إليها، على أن تظل خاضعة لهذه الاتفاقية.
## عدم الضمان
- تُقدَّم المعلومات السرية دون أي ضمان بشأن دقتها أو اكتمالها، ولا يتحمل أي من الطرفين أي مسؤولية عن استخدامها إلا وفق ما يرد في اتفاق كتابي مستقل.
## الجبر والتعويض
- يقر كل طرف بأن التعويض المالي وحده قد لا يكون كافياً لجبر الإخلال بهذه الاتفاقية، وأن للطرف المفصح الحق في طلب الأمر القضائي أو التنفيذ العيني إضافةً إلى أي وسيلة انتصاف أخرى.
## مدة الالتزامات
- تستمر الالتزامات الواردة في هذه الاتفاقية لمدة {{survival_years}} سنة (سنوات) بعد انتهاء مدتها، ولمدة بقاء أي معلومات سرية بوصفها سراً تجارياً.
## عدم قيام شراكة أو وكالة
- لا تنشئ هذه الاتفاقية أي شراكة أو مشروع مشترك أو وكالة أو علاقة عمل بين الطرفين.
## التنازل
- لا يجوز لأي من الطرفين التنازل عن أي من حقوقه أو التزاماته بموجب هذه الاتفاقية أو نقلها دون موافقة كتابية مسبقة من الطرف الآخر.
## الإشعارات
- يجب أن يكون أي إشعار بموجب هذه الاتفاقية كتابياً وأن يُسلَّم إلى عنوان الطرف الآخر المسجل أو إلى أي عنوان آخر يخطر به كتابةً.
## الاتفاق الكامل والتعديل والتنازل عن الحقوق
- تمثل هذه الاتفاقية الاتفاق الكامل بين الطرفين بشأن موضوعها.
- لا يكون أي تعديل لهذه الاتفاقية نافذاً ما لم يكن كتابياً وموقعاً من الطرفين.
- لا يُعد التأخر في استعمال أي حق أو عدم استعماله تنازلاً عنه.
## قابلية التجزئة
- إذا تقرر بطلان أي حكم من أحكام هذه الاتفاقية أو عدم قابليته للتنفيذ، ظلت الأحكام الأخرى سارية بكامل أثرها.
## حقوق الغير
- لا يحق لأي شخص من غير الطرفين المطالبة بإنفاذ أي حكم من أحكام هذه الاتفاقية.
## النسخ والتوقيع الإلكتروني
- يجوز تحرير هذه الاتفاقية من نسخ متعددة والتوقيع عليها بوسيلة توقيع إلكتروني موثوقة من مفوضين بالتوقيع.
## القانون الواجب التطبيق
- تخضع هذه الاتفاقية، وأي نزاع أو التزام غير تعاقدي ينشأ عنها أو يتصل بها، لقوانين {{governing_law}}.
## الاختصاص القضائي
- تختص محاكم {{governing_law}} حصرياً بنظر أي نزاع أو مطالبة تنشأ عن هذه الاتفاقية أو موضوعها أو إبرامها أو تتصل بها.
### التوقيع
أُبرمت هذه الاتفاقية وتسري اعتباراً من تاريخ السريان.
@sign {{party_a_name}}
@sign {{party_b_name}}
"""

SERVICE_AR_BODY = """# اتفاقية خدمات
تاريخ السريان: {{effective_date}}
### الأطراف
1. {{supplier_name}} («المورّد»)؛ و
2. {{client_name}} («العميل»).
### الشروط المتفق عليها
## الخدمات
- يقدم المورّد للعميل الخدمات التالية: {{services}}.
- يؤدي المورّد الخدمات بمهارة وعناية معقولتين ووفقاً للقانون المعمول به.
## الأتعاب والدفع
- يدفع العميل للمورّد {{fees}}.
- يصدر المورّد فواتير للعميل، ويسدد العميل كل فاتورة غير متنازع عليها خلال {{payment_days}} يوماً من استلامها.
## المدة والإنهاء
- تسري هذه الاتفاقية من تاريخ السريان وتستمر لمدة {{term_months}} شهراً، ما لم تُنهَ قبل ذلك وفق هذا البند.
- يجوز لأي من الطرفين إنهاء هذه الاتفاقية فوراً بإشعار كتابي إذا ارتكب الطرف الآخر إخلالاً جوهرياً ولم يعالجه خلال 30 يوماً من الإشعار الذي يطلب منه ذلك.
## السرية
- يلتزم كل طرف بالمحافظة على سرية جميع المعلومات غير المعلنة للطرف الآخر التي يتلقاها فيما يتصل بهذه الاتفاقية، وألا يستخدمها إلا لأداء الخدمات أو تلقيها.
## الملكية الفكرية
- يحتفظ كل طرف بملكية حقوقه الفكرية السابقة. وتنتقل إلى العميل ملكية المواد التي تُعد خصيصاً له بموجب هذه الاتفاقية عند السداد الكامل.
## المسؤولية
- لا شيء في هذه الاتفاقية يحد من المسؤولية التي لا يجوز الحد منها بموجب القانون.
- مع مراعاة الفقرة السابقة، تُحدد المسؤولية الإجمالية للمورّد بموجب هذه الاتفاقية بمبلغ الأتعاب المدفوعة أو المستحقة بموجبها.
## أحكام عامة
- تمثل هذه الاتفاقية الاتفاق الكامل بين الطرفين بشأن موضوعها.
- لا يكون أي تعديل نافذاً ما لم يكن كتابياً وموقعاً من الطرفين.
- لا يجوز لأي من الطرفين التنازل عن هذه الاتفاقية دون موافقة كتابية مسبقة من الآخر.
## القانون الواجب التطبيق والاختصاص القضائي
- تخضع هذه الاتفاقية وأي نزاع ينشأ عنها أو يتصل بها لقوانين {{governing_law}}، وتختص محاكم {{governing_law}} حصرياً بنظره.
### التوقيع
أُبرمت هذه الاتفاقية وتسري اعتباراً من تاريخ السريان.
@sign {{supplier_name}}
@sign {{client_name}}
"""


def _f(key, label, question, required=True, default=None):
    return {"key": key, "label": label, "question": question, "required": required, "default": default}


BUILTIN_TEMPLATES = [
    {
        "template_id": "builtin-nda-mutual",
        "tenant_id": "*",
        "name": "Mutual Confidentiality Agreement (NDA)",
        "doc_type": "NDA",
        "description": "Mutual non-disclosure agreement between two parties, with an optional deliverables clause.",
        "fields": [
            _f("party_a_name", "First party", "What is the full legal name of the first party?"),
            _f("party_b_name", "Second party", "What is the full legal name of the second party?"),
            _f("effective_date", "Effective date", "What is the effective date of the agreement?"),
            _f("purpose", "Subject of the relationship", "What is the potential relationship or project about (for example, a joint supply chain project)?"),
            _f("deliverables", "Deliverables", "Are there any deliverables? If so, what are they?", required=False),
            _f("term_years", "Term (years)", "How many years should the agreement run?", required=False, default="2"),
            _f("survival_years", "Confidentiality survival (years)", "For how many years after the term should confidentiality continue?", required=False, default="3"),
            _f("governing_law", "Governing law", "Which law should govern the agreement?", required=False, default="England and Wales"),
        ],
        "body": NDA_BODY,
    },
    {
        "template_id": "builtin-service-agreement",
        "tenant_id": "*",
        "name": "Services Agreement",
        "doc_type": "Service agreement",
        "description": "Basic agreement for a supplier providing services to a client for a fee.",
        "fields": [
            _f("supplier_name", "Supplier", "What is the full legal name of the supplier?"),
            _f("client_name", "Client", "What is the full legal name of the client?"),
            _f("effective_date", "Effective date", "What is the effective date of the agreement?"),
            _f("services", "Services", "What services will be provided?"),
            _f("fees", "Fees", "What are the fees (amount, currency and basis)?"),
            _f("payment_days", "Payment period (days)", "Within how many days must invoices be paid?", required=False, default="30"),
            _f("term_months", "Term (months)", "How many months should the agreement run?", required=False, default="12"),
            _f("governing_law", "Governing law", "Which law should govern the agreement?", required=False, default="England and Wales"),
        ],
        "body": SERVICE_BODY,
    },
    {
        "template_id": "builtin-nda-mutual-ar",
        "tenant_id": "*",
        "language": "ar",
        "name": "اتفاقية سرية متبادلة (NDA)",
        "doc_type": "NDA",
        "description": "Arabic mutual non-disclosure agreement between two parties, with an optional deliverables clause. اتفاقية عدم إفصاح متبادلة بين طرفين.",
        "fields": [
            _f("party_a_name", "الطرف الأول", "ما الاسم القانوني الكامل للطرف الأول؟"),
            _f("party_b_name", "الطرف الثاني", "ما الاسم القانوني الكامل للطرف الثاني؟"),
            _f("effective_date", "تاريخ السريان", "ما تاريخ سريان الاتفاقية؟"),
            _f("purpose", "موضوع العلاقة", "ما موضوع العلاقة أو المشروع المحتمل (مثلاً: مشروع مشترك في سلسلة الإمداد)؟"),
            _f("deliverables", "المخرجات", "هل توجد مخرجات؟ وإن وُجدت فما هي؟", required=False),
            _f("term_years", "المدة (بالسنوات)", "كم سنة تستمر الاتفاقية؟", required=False, default="2"),
            _f("survival_years", "استمرار السرية (بالسنوات)", "كم سنة تستمر السرية بعد انتهاء المدة؟", required=False, default="3"),
            _f("governing_law", "القانون الواجب التطبيق", "ما القانون الذي يحكم الاتفاقية؟", required=False, default="دولة الإمارات العربية المتحدة"),
        ],
        "body": NDA_AR_BODY,
    },
    {
        "template_id": "builtin-service-agreement-ar",
        "tenant_id": "*",
        "language": "ar",
        "name": "اتفاقية خدمات",
        "doc_type": "Service agreement",
        "description": "Arabic basic agreement for a supplier providing services to a client for a fee. اتفاقية أساسية لتقديم خدمات مقابل أتعاب.",
        "fields": [
            _f("supplier_name", "المورّد", "ما الاسم القانوني الكامل للمورّد؟"),
            _f("client_name", "العميل", "ما الاسم القانوني الكامل للعميل؟"),
            _f("effective_date", "تاريخ السريان", "ما تاريخ سريان الاتفاقية؟"),
            _f("services", "الخدمات", "ما الخدمات التي ستُقدَّم؟"),
            _f("fees", "الأتعاب", "ما الأتعاب (المبلغ والعملة وأساس الاحتساب)؟"),
            _f("payment_days", "مهلة الدفع (بالأيام)", "خلال كم يوماً تُسدَّد الفواتير؟", required=False, default="30"),
            _f("term_months", "المدة (بالأشهر)", "كم شهراً تستمر الاتفاقية؟", required=False, default="12"),
            _f("governing_law", "القانون الواجب التطبيق", "ما القانون الذي يحكم الاتفاقية؟", required=False, default="دولة الإمارات العربية المتحدة"),
        ],
        "body": SERVICE_AR_BODY,
    },
]
for _t in BUILTIN_TEMPLATES:
    _t.setdefault("language", "en")
