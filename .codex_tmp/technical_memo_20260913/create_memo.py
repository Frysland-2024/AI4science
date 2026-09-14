from pathlib import Path
import json, hashlib
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path('E:/AI4science')
WORK = ROOT / '.codex_tmp/technical_memo_20260913'
OUT = ROOT / 'outputs/XRD_技术细节备忘录.docx'
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.7)
sec.left_margin = sec.right_margin = Cm(2)
sec.footer_distance = Cm(.8)

def font(run, size=10.5, bold=None):
    run.font.name = 'Calibri'
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0,0,0)
    if bold is not None: run.bold = bold
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement('w:rFonts'); rpr.insert(0, fonts)
    fonts.set(qn('w:eastAsia'), '微软雅黑')

for name, size in [('Normal',10.5),('Title',22),('Subtitle',10),('Heading 1',16),('Heading 2',11.5)]:
    s = doc.styles[name]
    s.font.name = 'Calibri'; s.font.size = Pt(size); s.font.color.rgb = RGBColor(0,0,0)
    s.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), '微软雅黑')
    s.paragraph_format.space_after = Pt(6)
    s.paragraph_format.line_spacing = 1.23
    if name in ['Heading 1','Heading 2']:
        s.font.bold = True; s.paragraph_format.space_before = Pt(10)
        s.paragraph_format.keep_with_next = True
    if name == 'Title': s.paragraph_format.space_after = Pt(8)
    s.font.italic = False
    pp=s.element.get_or_add_pPr()
    for e in list(pp):
        if e.tag==qn('w:pBdr'): pp.remove(e)
    snap=OxmlElement('w:snapToGrid'); snap.set(qn('w:val'),'0'); pp.append(snap)

page_titles = []
def p(text, size=10.5, boldlead=False, style=None):
    para = doc.add_paragraph(style=style)
    para.paragraph_format.widow_control = True
    para.paragraph_format.line_spacing = Pt(15.5 if size >= 10 else 13)
    if boldlead and '：' in text:
        a,b=text.split('：',1); font(para.add_run(a+'：'),size,True); font(para.add_run(b),size)
    else: font(para.add_run(text),size)
    return para

def h(text, level=2):
    para = doc.add_paragraph(text, style=f'Heading {level}')
    para.paragraph_format.line_spacing = Pt(22 if level==1 else 17)
    for r in para.runs: font(r, 16 if level==1 else 11.5,True)
    return para

def page(title):
    para=h(title,1); para.paragraph_format.page_break_before=True; page_titles.append(title)

def table(headers, rows, widths, size=9.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    for c,w in zip(t.columns,widths): c.width=Cm(w)
    for c,w,tx in zip(t.rows[0].cells,widths,headers): c.width=Cm(w); c.text=tx
    repeat=OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        cells=t.add_row().cells
        for c,w,tx in zip(cells,widths,row): c.width=Cm(w); c.text=str(tx)
    props=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+edge); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
    props.append(borders)
    for ri,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr(); trpr.append(OxmlElement('w:cantSplit'))
        for ci,c in enumerate(row.cells):
            c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=c._tc.get_or_add_tcPr()
            mar=OxmlElement('w:tcMar')
            for e,v in [('top','70'),('bottom','70'),('left','90'),('right','90')]:
                x=OxmlElement('w:'+e); x.set(qn('w:w'),v); x.set(qn('w:type'),'dxa'); mar.append(x)
            tcpr.append(mar)
            if ri==0:
                sh=OxmlElement('w:shd'); sh.set(qn('w:fill'),'E7EBEF'); tcpr.append(sh)
            for para in c.paragraphs:
                para.paragraph_format.space_after=Pt(0); para.paragraph_format.line_spacing=Pt(13.5)
                para.paragraph_format.keep_with_next=False
                if ci>0 and len(para.text)<24 and '\n' not in para.text: para.alignment=WD_ALIGN_PARAGRAPH.CENTER
                for r in para.runs: font(r,size,ri==0)
    after=doc.add_paragraph(); after.paragraph_format.space_after=Pt(0); after.paragraph_format.space_before=Pt(0)
    after.paragraph_format.line_spacing=Pt(3); font(after.add_run(''),3)
    return t

def link(para,label,url,size=9):
    rel=para.part.relate_to(url,RT.HYPERLINK,is_external=True)
    hyp=OxmlElement('w:hyperlink'); hyp.set(qn('r:id'),rel)
    run=OxmlElement('w:r'); pr=OxmlElement('w:rPr')
    fs=OxmlElement('w:rFonts'); fs.set(qn('w:ascii'),'Calibri'); fs.set(qn('w:eastAsia'),'微软雅黑'); pr.append(fs)
    sz=OxmlElement('w:sz'); sz.set(qn('w:val'),str(int(size*2))); pr.append(sz)
    co=OxmlElement('w:color'); co.set(qn('w:val'),'000000'); pr.append(co)
    un=OxmlElement('w:u'); un.set(qn('w:val'),'single'); pr.append(un)
    run.append(pr); tx=OxmlElement('w:t'); tx.text=label; run.append(tx); hyp.append(run); para._p.append(hyp)

def source(num,title,items):
    para=p(f'[{num}] {title}',9.2); para.paragraph_format.space_after=Pt(3)
    for label,url in items:
        para=doc.add_paragraph(); para.paragraph_format.space_after=Pt(3); para.paragraph_format.line_spacing=1.05
        link(para,label,url,8.8)

# 1
doc.add_paragraph('XRD 技术细节备忘录',style='Title')
p('七晶系分类实验  配套导师汇报  2026年9月13日',10,style='Subtitle')
p('用于汇报时查参数、说明实现和回答追问。主线是：从同一晶体结构生成两条扰动谱，用分类损失学习晶系，再用 JS 损失约束两次预测接近。')
h('1  常用设置速查',1); page_titles.append('1  常用设置速查')
table(['项目','正式分类实验设置'],[
('输入','2θ 为 10°–80°，间隔 0.02°，共 3,501 点，单通道'),
('输出','7 个晶系的概率，取最大概率对应的类别'),
('模型','一维 ResNet-18，GroupNorm，约 1,301 万参数'),
('每次训练输入','16 个母结构，每个结构生成 2 条谱，共 32 条谱'),
('损失','两条谱的平均交叉熵；JS 组另加 60 × JS 散度'),
('优化器','AdamW，学习率 1×10⁻⁴，weight decay 1×10⁻⁴，学习率恒定'),
('训练时长','最多 100 epoch；每 10 epoch 验证；启用 early stopping'),
('重复设置','5 个训练种子，两种方法逐种子配对'),
('训练谱与评估谱','训练在线重采样；验证与测试使用预先固定的谱'),
], [3,14])
h('数据从哪里来')
p('14,060 个 Materials Project 晶体结构，先按晶系分层划分，再生成谱。训练、验证、测试分别为 9,842、2,109、2,109 个母结构，划分种子为 20260726。[1]')
p('“母结构”指生成谱的那份晶体结构。同一母结构的所有扰动谱归属同一数据集。谱图数可以随训练增加，独立晶体结构数仍是 14,060。')
p('类别索引固定为：0 三斜、1 单斜、2 正交、3 四方、4 三方、5 六方、6 立方。三方和六方分别作为一类，读取标签和混淆矩阵时按这个顺序。')
p('阅读位置：模型见第 2 页，JS 与选参见第 3 页，训练见第 4 页，扰动见第 5–6 页，真实谱见第 7 页，常见追问见第 8 页，出处见第 9 页。',9)

# 2
page('2  Backbone 的选择与配置')
p('Backbone 是从一维谱中提取特征的网络。项目采用 ML4pXRDs 的一维 ResNet 架构，并移植到 PyTorch。正式 ERM 和 JS 两组均使用同一套 ResNet-18-GN。[2]')
h('选择过程')
p('早期开发比较中，PAMPT-B3 的 level0 验证 Macro-F1 为 0.5327，ResNet-18-GN 为 0.6522；对应训练准确率为 0.6385 和 1.0000。这个结果支持改用能充分拟合训练数据的 ResNet。它属于开发阶段比较，数值不能代替正式测试结果。[3]')
p('随后分别试过平方根预处理、改用 Adam、5 epoch 学习率预热加余弦衰减，均未达到预先规定的验证提升门槛。最终保留 identity 预处理、AdamW 和恒定学习率。GN 沿用该架构设置，现有结论不包含 GN 对 BN 的独立优劣比较。[3]')
h('实际网络结构')
table(['位置','配置','输出 通道数 × 长度'],[
('输入','单通道强度序列','1 × 3501'),
('入口卷积','kernel=7，stride=2；GN + ReLU','64 × 1751'),
('最大池化','kernel=3，stride=2','64 × 876'),
('残差阶段 1','2 个残差块，kernel=9，阶段 stride=1','64 × 876'),
('残差阶段 2','2 个残差块，kernel=9，阶段 stride=4','128 × 219'),
('残差阶段 3','2 个残差块，kernel=9，阶段 stride=4','256 × 55'),
('残差阶段 4','2 个残差块，kernel=9，阶段 stride=4','512 × 14'),
('末端两层','Flatten 7168；Linear 7168→256；Linear 256→7','256 维特征 / 7 个 logits'),
],[3,8.3,5.7],9.3)
p('每个残差块含两次卷积与跳连。GN 使用 32 组、eps=0.001。末端两层全连接之间没有额外激活，模型没有 dropout，也没有全局平均池化。[2]')
p('GN 在单个样本内按通道分组归一化，不需要依赖整个 batch 的均值与方差。这里说明它如何工作，并不据此声称项目已经证明 GN 更优。[2]')
h('输入处理和初始化')
p('谱先完成模拟或真实谱网格对齐，再除以自身最大强度。identity 表示之后不再加平方根、对数、平滑或基线扣除。模拟预训练从随机初始化开始，不加载 ImageNet 权重。卷积、全连接层和 GN 的初始化均在模型源码中明确实现。[1–2]')

# 3
page('3  JS 如何计算  λ 如何选择')
h('JS 约束什么')
p('同一母结构的两条谱输入同一个模型，得到两组七类概率 p₁、p₂。JS 即 Jensen–Shannon 散度，衡量两组概率有多不一样。它比较完整概率分布，不只比较最终类别是否相同。[4]')
for tx in [
    'p₁ = softmax(f(x₁))，p₂ = softmax(f(x₂))，m = (p₁ + p₂) / 2',
    'L分类 = [CE(f(x₁), y) + CE(f(x₂), y)] / 2',
    'JS(p₁, p₂) = [KL(p₁ ∥ m) + KL(p₂ ∥ m)] / 2',
    'L总 = L分类 + λ × JS(p₁, p₂)    正式 JS 组 λ = 60',
]: p(tx,10)
p('CE 是交叉熵，负责把预测拉向真实晶系；JS 负责让同一母结构的两次预测接近。只用 JS 时，模型给所有谱相同预测也能让 JS 为零，所以分类损失必须保留。')
p('实现使用自然对数，按 batch 求平均。两条分支都参与反向传播，不设教师模型，不使用伪标签、温度缩放或特征距离损失。Dynamic ERM 同样用两条谱计算 CE，仅不加 JS 项。[4]')
h('先定候选尺度  再用验证集选值')
p('第一步只用训练集检查梯度尺度，固定候选 λ 为 3、30、60。加权 JS 梯度相对分类梯度的中位数比分别为 0.087859、0.877058、1.754115。这里用梯度大小判断辅助项是否太弱或太强，不是比较两个 loss 的数值。[5]')
p('第二步使用开发种子 20260710、评估种子 20260720 训练并比较候选。先要求 in-range Macro-F1 不低于 ERM 减 0.01，再选六个单项 OOD 面板平均 Macro-F1 最高者。若并列，先看 in-range，再选较小 λ。[5]')
table(['候选','验证 in-range','验证平均 OOD','选择结果'],[
('Dynamic ERM','0.714013','0.666471','参照'),
('JS λ=3','0.718417','0.676134','通过范围内约束'),
('JS λ=30','0.716428','0.676164','通过范围内约束'),
('JS λ=60','0.729806','0.699742','通过约束，OOD 最高'),
],[4,4,4,5],9.5)
p('λ=60 确定后保持不变，再开展五个种子的正式重复训练及模拟 Test、RRUFF、CNRS 评估。真实域结果没有用于重选 λ。60 是这个损失尺度和任务下的选择，不能直接当作其他模型的通用参数。')
p('实现细节：Train-only 中 λ=60 的梯度尺度由 λ=30 的同一批梯度记录逐条倍增并重算检查条件得到；后续验证阶段才单独训练三个候选。这两步承担不同用途。[5]',9)

# 4
page('4  正式训练与模型保存')
p('以下是产生汇报结果的历史正式训练设置。当前公开 runner 只提供简化训练接口，不能仅凭其默认参数重建这套实验。[6]')
table(['设置','实际做法'],[
('优化','AdamW，lr=1×10⁻⁴，weight decay=1×10⁻⁴；学习率恒定'),
('训练预算','上限 100 epoch / 61,600 step；每 epoch 616 step'),
('一个 step','16 个母结构，各在线生成 2 条谱，合计 32 条；一次反向更新'),
('验证频率','每 6,160 step，即每 10 epoch，评估固定验证谱'),
('早停条件','至少训练 50 epoch；连续 3 次验证没有足够的 OOD 改善就停止'),
('改善阈值','平均单项 OOD Macro-F1 相对最近一次实质改善的参考值提高超过 0.002'),
('保存模型','按 OOD 主指标选择；差值在 0.002 内时用 in-range 打破平局'),
],[3.3,13.7],9.4)
p('仅靠 in-range 打破平局可更新 best，但不会清零早停计数；in-range 也相同时保留较早轮。50 epoch 是最早允许停止的时间，best 可以出现在第 50 轮之前。最终测试读取 best checkpoint。[6]')
table(['训练种子','ERM 最佳轮','ERM 结束轮','JS 最佳轮','JS 结束轮'],[
('20260711','80','90 早停','40','70 早停'),
('20260712','90','100 上限','80','100 上限'),
('20260713','100','100 上限','80','100 上限'),
('20260714','90','100 上限','30','60 早停'),
('20260715','80','100 上限','60','90 早停'),
],[3.7,3.2,3.5,3.2,3.4],9.2)
h('训练时遵循的原则')
p('可比性：两组使用同一模型、母结构、双谱生成规则、优化器、训练上限和早停规则，随机种子配对。实际训练步数会随早停发生变化，不能说十次运行都训练了相同步数。',boldlead=True)
p('完整记录：历史固定预算采样器会循环补齐尾 batch。616×16=9,856 次母结构取样，略多于 9,842 个训练母结构，因此这里的一个 epoch 不等于每个结构恰好出现一次。',boldlead=True)
p('选择隔离：训练集用于更新权重；验证集用于早停、checkpoint 和 λ 选择；测试集用于冻结后的评估。读到测试结果后不再更换权重、种子或扰动范围。',boldlead=True)
p('运行配置：历史启动脚本使用 bfloat16 混合精度，数值异常回退 float32，启用 fused AdamW；验证 batch=256。这些是运行设置，不改变 CE+JS 的目标定义。[6]',9.4)

# 5
page('5  五种扰动的数值范围')
p('U(a,b) 表示区间内均匀采样，LogU(a,b) 表示在对数尺度上均匀采样。p 是每条谱启用该扰动的概率。训练与 in-range 验证使用相同分布，OOD 表示超出训练范围的测量条件。[7]')
table(['扰动','训练与 in-range','对应单项 OOD'],[
('峰位整体偏移','Δ2θ ~ U(−0.2, 0.2)°\np=0.5','负向 U(−0.5, −0.2)°\n正向 U(0.2, 0.5)°\n两个面板，均 p=1'),
('峰展宽','FWHM ~ U(0.08, 0.20)°\np=1','FWHM ~ U(0.20, 0.35)°\np=1'),
('择优取向','March–Dollase r ~ U(0.8, 1.0)\np=0.7；低指数反射候选轴最多 16 个','r ~ U(0.5, 0.8)\np=1；其他扰动保留训练分布'),
('平滑背景','三阶多项式\n背景/参考峰高比 U(0, 0.02)，p=0.5\n起伏 U(0.15, 0.45)，floor=0.15','高斯过程背景\n背景/参考峰高比 U(0.02, 0.05)，p=1\n起伏 U(0.35, 0.90)，floor=0.20\n33 个锚点，长度尺度 0.12'),
('计数与读出噪声','Poisson–Gaussian，p=1\n计数尺度 C ~ LogU(2500, 40000)\n读出标准差 σe ~ U(0, 2) counts','Poisson–Gaussian，p=1\nC ~ LogU(100, 2500)\nσe ~ U(0, 5) counts'),
],[2.8,7.1,7.1],9.1)
h('这些参数分别改变什么')
p('峰移给所有峰加同一个角度偏移，近似仪器零点误差。展宽用统一的高斯 FWHM 改变峰宽，σ=FWHM/2.35482。它们没有改动晶格或原子坐标，也不等同于晶格应变和完整的尺寸展宽模型。')
p('择优取向按反射方向重分配积分强度。r=1 为无取向偏好，本项目区间内 r 越小通常扰动越强；实际变化还取决于所选方向。相同参数不会把每个峰都乘上同一个数。')
p('背景比相对 0.08° 峰宽下的参考峰高定义。谱峰展宽后，背景相对当前峰高的比例可能更高。floor 控制背景底部比例；GP 长度尺度定义在归一化坐标上，0.12 不能读成 0.12°。GP 起伏幅度随后被形状归一化消去，不宜用它解释背景更强。')
p('噪声先把强度换成期望计数 I×C，再采 Poisson 计数并加计数域高斯读出噪声，最后截去负值并归一化。C 越小，相对计数噪声越强。这里的 2 和 5 是 counts，不是 2% 或 5%。')
h('范围的依据')
p('本地已完成论文、补充材料、原作者代码和当前实现的交叉核查，再据此确定训练与 OOD 区间。文献给出机制与数量级，最终配置固定本项目的工程取舍。具体核查过程和逐项依据见第 6–7 页。')

# Literature process
page('6  文献核查与定范围的过程')
p('这套范围有本地阅读和核查记录。处理顺序是：筛选可用论文，摘录原始参数，核对单位、公式和代码，再确定本项目的训练区间与压力测试区间。')
h('先筛选能提供参数依据的论文')
p('筛选要求包括：给出粉末 XRD 的直接数值；能说明对应的物理公式或算子；能找到论文到代码的映射。最后保留 Szymanski 2021、SimXRD-4M、XQueryer、Salgado 2023、CPICANN、Lee 2023、Schopmans 2023 七篇核心参考。')
p('Vecsei 2019 补充背景和噪声依据；Oviedo 与 XRDMatch 用于增强方法参考。4D-STEM 的像素漂移、薄膜特有变化、数组位移等，不能不经换算就拿来规定粉末谱的角度和强度范围。',9.8)
h('逐项摘录  保留原始定义')
p('历史原始参数表记录了来源、数值、单位、分布、归一化、公式、任务、训练或测试用途、原文位置和代码核验状态，并分别判断“机制可信度”和“数值能否迁移”。论文范围、补充材料参数和仓库默认值分开保留。')
p('例如，晶格应变先改变晶面间距，再改变峰位，不能并入全谱零点平移；晶粒尺寸要经 Scherrer 关系换成角度相关峰宽；背景面积缩放、峰高比例和噪声标准差也不能混用。')
h('对照代码  确认参数真正改变了什么')
p('核查不止看参数名，还追到采样函数、前向生成和归一化顺序。历史五扰动对照表记录了 SimXRD 与本项目的差异，例如 SimXRD 的 mixture_noise_ratio 在对应源码中生成正均匀噪声，不能直接当作高斯标准差。')
p('V6 先登记工程候选，V7 再加入 March–Dollase 取向和计数噪声。2026年7月15日因缺少依据，移除了“最多同时出现两个强扰动”的拒绝规则；7月16日记录联合参数范围尚不足以冻结，保留独立采样方案。后续采用的算子和范围见第 5、8 页。')
h('固定范围后检查参数抽样与谱形')
p('V9 核查脚本读取已标为 formal_frozen 的配置，用 dev_3500 的 3,500 个母结构、每结构 2 个视图，检查每面板 7,000 次参数采样；谱形检查另取每类 3 个母结构，共 42 条谱/面板。这是对既定范围的审计，没有运行训练或自动搜索范围。')
p('训练与 in-range 的 42 条检查谱均通过；ood_all 有 10 条未过前 20 强峰的保留率门槛，作为强扰动诊断保留。因此这一步检查的是范围及谱形是否可用，不能据此宣称所有强扰动都保留了足够的分类信息。')
p('正式方法比较共用冻结范围。早期文档提出过启用概率敏感性实验，但提出方案不等于完成最优搜索；现有范围应称为经文献与代码核查后采用的工程设定。启用概率 p 是训练策略参数。',9.8)
h('本地记录入口')
hist='https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/'
for entries in [
    [('七篇核心论文', (ROOT/'01_literature/xrd_perturbation_core/core_paper_chain.md').as_uri()), ('候选筛查记录', (ROOT/'01_literature/xrd_perturbation_core/local_candidate_audit.md').as_uri()), ('逐篇精读', (ROOT/'01_literature/xrd_perturbation_core/paper_map/PAPER_ANALYSIS.md').as_uri())],
    [('原始参数证据表',hist+'xrd_robustness/reports/literature_parameter_raw.csv'),('五扰动源码对照表',hist+'xrd_robustness/reports/V8_FIVE_PERTURBATION_COMPARISON.csv')],
    [('早期范围与概率方案',hist+'00_project_context/V6_PHYSICS_EVIDENCE_AND_PROBABILITY_PLAN.md'),('7月修订记录', (ROOT/'archive/paper-ready-cleanup-20260908/docs/PROJECT_HISTORY.md').as_uri())],
    [('V9 冻结审核结果',hist+'xrd_robustness/reports/v9_method_transfer_perturbation_freeze.json'),('对应审核脚本',hist+'xrd_robustness/scripts/audit_v9_perturbation_freeze.py')],
    [('当前五类扰动的依据汇总',(ROOT/'archive/paper-ready-cleanup-20260908/docs/PXRD_PERTURBATION_EVIDENCE.md').as_uri())],
]:
    para=doc.add_paragraph(); para.paragraph_format.space_after=Pt(2); para.paragraph_format.line_spacing=Pt(12)
    for idx,(label,url) in enumerate(entries):
        if idx: font(para.add_run('   /   '),8.8)
        link(para,label,url,8.8)

# Individual literature anchors
page('7  五类扰动的文献数值与取舍')
p('下列数字保留来源中的定义；“本项目采用”对应第 5 页的正式配置。论文数值用于判断数量级，训练与 OOD 的分界仍由本项目确定。')

def paper_ref(para, label, filename):
    font(para.add_run('  '),9)
    link(para,label,(ROOT/'01_literature/literature_zones/01_core_xrd_perturbation_phase_identification'/filename).as_uri(),8.8)

h('峰移  以全谱角度平移为参照')
para=p('Szymanski 2021 作者仓库的整体峰移默认上限为 ±0.5°；SimXRD-4M 附录 B.4 给出全局零点偏移 ±1.2°。本项目采用较窄的 ±0.2° 训练，并用绝对偏移 0.2°–0.5° 测试。0.2° 是本项目的区间分界；Szymanski 正文中的晶格应变范围属于另一种变化。')
paper_ref(para,'SimXRD PDF 第 21 页','02_SimXRD_2025_OpenReview.pdf')
font(para.add_run('  '),9)
link(para,'Szymanski 仓库 README 第 78 行',(ROOT/'02_code_repositories/xrd_perturbation_core/extracted_verified/XRD-AutoAnalyzer-main/XRD-AutoAnalyzer-main/README.md').as_uri(),8.8)

h('展宽  先由公式判断角度量级')
para=p('Salgado 2023 表 1 的一组 Caglioti 条件为 U=V=0、W∈[0.001,0.1]。代入 FWHM²=U tan²θ+V tanθ+W，可算得 FWHM≈0.032°–0.316°。本项目采用统一高斯峰宽：训练 0.08°–0.20°，压力测试 0.20°–0.35°。这是参考量级后的简化与扩展，不是完整复用论文峰形。')
paper_ref(para,'Salgado PDF 第 10 页  式 8 与表 1','04_Salgado_2023_Automated_Classification_Big_XRD.pdf')

h('择优取向  参考方向相关的强度变化')
para=p('Lee 2023 使用 modified March 模型，G1 在 0.5–0.9 随机取值，并从 16 个主要低指数峰对应方向中选优选方向。这支持用共同方向系统地改变峰强。本项目的 March–Dollase r 采用训练 0.8–1.0、OOD 0.5–0.8；模型定义与参数范围没有逐项照搬，r=1 为本实现的无取向偏好状态。')
paper_ref(para,'Lee PDF 第 12 页  实验部分','07_Lee_2023_Advanced_XRD_Analysis.pdf')

h('背景  同时核对形状和幅度的定义')
para=p('SimXRD-4M 附录使用六阶多项式背景，并给出 2% 条件；本地原作者代码另有 background_ratio=0.05 的默认值。Schopmans 的补充材料核查记录支持 GP 背景。本项目选三阶多项式、参考峰高比 0–0.02 作为训练，GP 与 0.02–0.05 作为 OOD；阶数、GP 长度尺度和区间分界都是当前实现的取舍。')
paper_ref(para,'SimXRD PDF 第 22 页','02_SimXRD_2025_OpenReview.pdf')

h('噪声  从归一化强度参照转为计数模型')
para=p('Szymanski 2021 的测试使用最高峰强度 1%–5% 的高斯噪声幅度；Schopmans SI 的本地核查记录给出归一化强度域加性高斯标准差 0–0.02。本项目正式实现改用 Poisson–Gaussian，计数尺度 C 为训练 2,500–40,000、OOD 100–2,500，并另加读出噪声。它们不是文献高斯标准差的直接换算。')
paper_ref(para,'Szymanski PDF 第 5 页','01_Szymanski_2021_XRD_AutoAnalyzer.pdf')
p('理解计数尺度时，可在期望强度 I=1、忽略读出噪声的参考点看 1/√C：训练约 0.5%–2%，OOD 约 2%–10%。这只是单点 Poisson 相对波动的量级检查，不能替代整张归一化谱的噪声分布。',9.5)

para=p('查证说明：Schopmans SI 本地仅保留历史核查笔记及官方链接，未保存 SI PDF。',9)
link(para,' 精读记录中的 Schopmans 条目',(ROOT/'01_literature/xrd_perturbation_core/paper_map/PAPER_ANALYSIS.md').as_uri(),8.8)
font(para.add_run('  '),9)
link(para,'SI 官方链接','https://www.rsc.org/suppdata/d3/dd/d3dd00071k/d3dd00071k1.pdf',8.8)

# 8
page('8  动态采样与参数版本')
h('训练中动态改变的内容')
p('每次取到一个母结构，读取固定的理想反射峰表，再独立采样两套测量参数并生成两条谱。母结构和晶系标签不变，变化的是峰位偏移、峰宽、取向参数、背景形状和噪声实现。[7]')
p('生成顺序：先按取向改变峰强，再做全谱峰移与高斯展宽，之后加背景和计数噪声，最后截去负值并作最大值归一化。',boldlead=True)
p('随机种子由运行种子、材料编号、epoch、step 和 view 编号等上下文确定。同一上下文可复现同一条谱，更换上下文会重新采样。训练不会一次存好所有增强谱再反复循环。')
p('范围固定：正式训练中，U(−0.2,0.2) 等区间和启用概率保持不变。没有随 epoch 逐步扩大范围的课程式训练，也没有用模型误差自动搜索更难扰动。动态的是区间内的取值。',boldlead=True)
p('评估固定：先生成并保存验证和测试参数清单，再让各方法使用同一批固定谱。正式模拟评估种子为 20260721、20260722、20260723，与训练种子分开。',boldlead=True)
h('实际测试面板的组成')
table(['面板组','设置与统计用途'],[
('level0','FWHM 固定 0.08°；无峰移、背景、取向扰动和附加随机噪声'),
('in-range','使用训练分布，具体样本和随机状态在评估时固定'),
('六个单项 OOD','负峰移、正峰移、展宽、噪声、背景、纹理；六项等权平均构成主 OOD 指标'),
('三个组合 OOD','正峰移+展宽；背景+噪声；纹理+负峰移；目标范围沿用第 5 页'),
('ood_all','峰移 U(−0.5,0.5)°，其余四项用更强设置；峰移取值可能落回训练范围'),
],[3.5,13.5],9.4)
p('面板不是统一的“只动一项、其余都干净”：纹理 OOD 保留其他训练扰动；峰移、展宽和背景单项面板的非目标因素采用基准设置，噪声算子关闭。汇报的 +5.46 pp 对应六个单项面板的平均值，不包含组合面板或 ood_all。')
h('旧记录与当前设置如何区分')
p('V7 candidate 与正式 V9 的共同面板参数相同，V9 增加了三个二因素组合面板，并未逐轮调大训练范围。更早的百分比高斯噪声属于旧表示或文献参照，不能直接换算成当前 counts 参数。正式配置采用 Poisson–Gaussian 和 March–Dollase 模型。[7]')
p('配置开关优先于参数名字：level0 虽保留 noise_model=poisson 和 C=40000 字段，冻结参数清单明确 noise_active=false。它是一条有 0.08° 峰宽的无附加随机噪声基准谱，并非理想 δ 尖峰。现有 Methods 将它写成带 Poisson 噪声，此处按历史参数清单和执行代码更正。[7]',boldlead=True)
p('质量阈值包括峰保留率、强度保留率、负值裁剪比例等。配置里写了阈值，不等于所有调用都执行拒绝重采样；公开 OnlineViewFactory 的质量检查可选，当前公开 runner 默认未启用。这项开关也属于复现设置。[7]',9.4)

# 7
page('9  真实谱适配与零样本评估')
h('RRUFF 301  使用少量真实标注更新末端层')
p('每个晶系 43 条谱，其中 10 条进入适配池、33 条进入固定测试集，合计 70/231。每次从适配池抽取每类 K=1、2、5 条，共 7、14、35 条作为 support。5 个预训练种子配合 5 个抽样种子，每档形成 25 组配对比较。[8]')
p('卷积和残差块冻结，更新 embedding 与 head 两个全连接层，即 7168→256 和 256→7。每次适配从对应模拟预训练权重开始，结束后恢复，避免上一组 support 的训练残留到下一组。')
p('适配仅用 support 的交叉熵，不再加 JS。AdamW 学习率为 1×10⁻⁴，每轮把全部 support 作为一个 batch，所以 1 epoch 就是 1 step。上限 200 轮，按 support loss 早停：min_delta=0.0001，patience=20。测试集不参与停止判断。')
table(['每类 K','总标注数','ERM 实际轮数','JS 实际轮数','Macro-F1 增益'],[
('1','7','86–193','93–182','+4.33 pp'),
('2','14','144–200','157–200','+4.60 pp'),
('5','35','均为 200','均为 200','+5.45 pp'),
],[2,2.7,4,4,4.3],9.2)
p('实际轮数来自 150 条历史运行记录。适配脚本没有显式冻结 weight_decay，使用当时 AdamW 默认，不能抄成模拟训练的 1×10⁻⁴。结果已回查到存储预测；完整的事前抽样计划和运行环境记录仍有限，宜称“经回查核验的固定测试集结果”。[8]',9.4)
h('CNRS 318  冻结模型直接预测')
p('CNRS 来自另一套实测谱来源，共 318 个独立母体，不使用其标签适配、选 λ 或挑 checkpoint。七类数量按固定类别顺序为 21/87/77/41/33/12/47，属于自然不平衡数据。[9]')
p('按原记录波长，用 Bragg 关系换算到 1.5406 Å，再线性插值到 10°–80° 的共同网格并作最大值归一化。越出原谱覆盖范围时，当前预处理实现使用端点值延拓。波长换算不是给所有峰加同一个零点偏移。')
p('五个种子的平均 Macro-F1 为 0.1884/0.2071，ERM/JS 配对提升 +1.87 pp，5/5 为正。分层配对母体 bootstrap 的 95% 区间为 [−0.009339, 0.046107]。区间跨零说明效应估计仍有较大抽样不确定性，应与五次配对结果一起报告。[9]')
p('RRUFF 检查同域少样本适配，CNRS 检查独立来源的直接迁移。两者不能合成一个分数，也不能把 CNRS 的零样本改善写成已经解决真实仪器上的通用识别。')

# 8
page('10  汇报时容易追问的问题')
h('模型为什么不会只学到所有谱都一样')
p('JS 鼓励同源谱的预测接近，交叉熵同时要求预测真实晶系。两个目标共同约束模型。只让预测一致并不足以得到正确分类，因此不能只看 JS loss 下降就判断训练成功。')
h('做了扰动后  还是原来的晶体吗')
p('在这个分类实验中，扰动作用于固定母结构的反射峰和观测谱，没有改动原子坐标、晶格或标签。它表达的是同一结构的不同测量。很强扰动仍可能遮住判别信息，所以“标签不变”并不保证每条谱都容易分类。')
h('收益是不是来自更多训练数据')
p('两组每个母结构都生成两条谱，并对两条谱计算 CE。两组使用相同扰动分布，JS 新增的是同源概率一致性项。训练上限和早停规则相同，实际轮数差异已在第 4 页列出。')
h('数据是否彻底没有泄漏')
p('当前划分保证精确母结构不跨集合，不保证化学式、结构原型或材料家族互不重叠。RRUFF 的适配池与测试集没有相同 ID 或完全相同存储谱，但有共享矿物名。因此结果不等同于未见材料家族的泛化能力。[1、8]')
h('Macro F1  提升 5 个百分点怎么理解')
p('先按每个晶系计算 F1，再对七类取平均。0.65 升到 0.70 是增加 5 个百分点，不是相对提高 5%。多次种子的均值与标准差、逐类支持数和 Accuracy 要同时看。CNRS 的“逐种子平均 F1”和“合并全部预测后的 pooled F1”计算顺序不同，数值不能混用。[9]')
h('五次重复和 25 次适配是否代表同样的证据')
p('五次模拟训练是五组不同训练种子。RRUFF 每档 25 次由 5 个预训练种子乘 5 个 support 抽样种子得到，不是 25 次独立预训练。CNRS 的 bootstrap 在晶系内重采样母体，并把同一份抽样用于两种方法和五个固定种子，没有重新抽训练种子。')
h('置信度降低是否等于校准改善')
p('不能仅靠最大概率降低判断。现有模拟和 CNRS 分析同时检查 ECE、NLL、Brier 与分类指标，结果总体改善，但 CNRS 的绝对准确率和校准水平仍低。RRUFF 未保存可用于同样校准计算的完整概率，不能把其他数据集的 ECE 结论移过去。[9]')
h('PPT 第 8 页的定量反演如何接着做')
p('分类约束针对晶系概率。反演 a、c、零点偏移和 FWHM 时，需要把结构参数与测量参数分开，再用前向模型检查重建谱，并评估参数误差及参数间混淆。谱能重建得相似，也可能有多组参数解释它。当前分类增益本身不能证明反演参数已正确。')

# 9
page('11  参数与记录出处')
p('正文按当前冻结配置、源码和历史正式运行记录交叉核对。链接用于定位原始依据。历史 Git 文件固定到 f36be82b 提交，避免把当前公开接口的默认值当作历史设置。',9.5)
def local(label,path): return (label,(ROOT/path).as_uri())
gitbase='https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/'
source('1','任务 数据和输入',[local('docs/METHODS.md','docs/METHODS.md'),local('xrd_robustness/configs/data.method_transfer.structure_split.json','xrd_robustness/configs/data.method_transfer.structure_split.json')])
source('2','模型实现与来源',[local('models/ml4pxrd_resnet1d.py  配置与网络结构 第 33–50 149 197–249 行','xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py'),('ML4pXRDs 原始项目','https://github.com/aimat-lab/ML4pXRDs'),('Group Normalization 原论文','https://arxiv.org/abs/1803.08494')])
source('3','Backbone 和训练方式的开发比较',[local('PROJECT_HISTORY.md  第 599–631 行','archive/paper-ready-cleanup-20260908/docs/PROJECT_HISTORY.md'),('历史 clean A/B/C 对比报告',gitbase+'xrd_robustness/reports/cnn_contract_clean_abc_summary.md')])
source('4','JS 损失实现',[local('training/objectives.py  第 35–100 行','xrd_robustness/src/xrd_robustness/training/objectives.py'),('PyTorch kl_div 说明','https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.kl_div.html')])
source('5','λ 候选与选择记录',[local('PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md  第 405–451 行','archive/paper-ready-cleanup-20260908/docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md'),('历史 four-run 冻结协议',gitbase+'xrd_robustness/configs/v9_resnet_js_four_run.preregistered.json')])
source('6','正式训练和早停',[('历史 ten-run 协议',gitbase+'xrd_robustness/configs/v9_resnet_js_ten_run.preregistered.json'),('历史十次训练汇总  最佳轮数与停止状态',gitbase+'xrd_robustness/reports/v9_resnet_js_ten_run_summary.json'),('历史运行脚本  混合精度与优化器设置',gitbase+'xrd_robustness/scripts/run_v9_resnet_js_ten_run.sh'),local('docs/REPRODUCIBILITY.md  公开 runner 与历史流程的区别','docs/REPRODUCIBILITY.md')])
source('7','扰动范围与实际启用状态',[local('configs/simulation.method_transfer.frozen.json','xrd_robustness/configs/simulation.method_transfer.frozen.json'),local('src/xrd_robustness/online_views.py','xrd_robustness/src/xrd_robustness/online_views.py'),local('src/xrd_robustness/simulator.py  第 225–237 行噪声开关','xrd_robustness/src/xrd_robustness/simulator.py'),local('v9_method_transfer_test_seed_20260721.csv  第 2 行 level0 参数','xrd_robustness/data/formal_14060/manifests/v9_method_transfer_test_seed_20260721.csv')])
source('8','RRUFF 适配与原始结果',[local('tmp/run_rruff301_confirmatory.py  第 161–221 行适配训练','tmp/run_rruff301_confirmatory.py'),local('rruff301_fewshot_runs.json  实际轮数和预测结果','xrd_robustness/data/real_xrd/rruff371/results/rruff301_fewshot_runs.json'),local('reports/RRUFF301_COMPOSITION_AUDIT.md','xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md')])
source('9','模拟测试 CNRS 与概率质量',[local('reports/RESULTS.md','xrd_robustness/reports/RESULTS.md'),local('reports/CNRS_318_RESULTS.md','xrd_robustness/reports/CNRS_318_RESULTS.md'),local('scripts/prepare_cnrs318_eval.py  波长转换与插值','xrd_robustness/scripts/prepare_cnrs318_eval.py')])

# Useful page numbers, no running header.
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
font(footer.add_run(''),9)
field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE')
footer._p.append(field)
doc.core_properties.title='XRD 技术细节备忘录'
doc.core_properties.subject='七晶系分类的模型、JS、参数、扰动、训练与评估'
doc.core_properties.author=''
doc.core_properties.keywords='XRD,ResNet,JS,early stopping,技术备忘录'
for para in doc.paragraphs:
    pp=para._p.get_or_add_pPr()
    for e in list(pp):
        if e.tag in [qn('w:pBdr'),qn('w:snapToGrid')]: pp.remove(e)
    snap=OxmlElement('w:snapToGrid'); snap.set(qn('w:val'),'0'); pp.append(snap)
for t in doc.tables:
    for row in t.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                snap=OxmlElement('w:snapToGrid'); snap.set(qn('w:val'),'0'); para._p.get_or_add_pPr().append(snap)
WORK.mkdir(parents=True,exist_ok=True)
OUT.parent.mkdir(parents=True,exist_ok=True)
doc.save(OUT)
text='\n'.join([para.text for para in doc.paragraphs]+[c.text for t in doc.tables for row in t.rows for c in row.cells])
(WORK/'content_review.txt').write_text(text,encoding='utf-8')
(WORK/'build_metadata.json').write_text(json.dumps({'output':str(OUT),'source_ppt':str(ROOT/'outputs/XRD_导师汇报.pptx'),'source_ppt_sha256':hashlib.sha256((ROOT/'outputs/XRD_导师汇报.pptx').read_bytes()).hexdigest(),'page_titles':page_titles},ensure_ascii=False,indent=2),encoding='utf-8')
print(OUT)
print('paragraphs',len(doc.paragraphs),'tables',len(doc.tables))
