// ============================================================
// GreenValue AI — Database Seed Script
// Creates realistic fake data for development & testing
// Usage:  npx ts-node scripts/seed.ts
// ============================================================

import { PrismaClient, Prisma, Role, AnalysisStatus, EnergyLabel, ReportFormat } from '@prisma/client';
import * as bcrypt from 'bcrypt';
import { randomUUID } from 'crypto';

const prisma = new PrismaClient();

// ── Helpers ─────────────────────────────────────────────────

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomFloat(min: number, max: number, decimals = 2): number {
  return parseFloat((Math.random() * (max - min) + min).toFixed(decimals));
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function daysAgo(days: number): Date {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d;
}

// ── Seed Data ───────────────────────────────────────────────

const TURKISH_CITIES = [
  { city: 'Istanbul', districts: ['Kadıköy', 'Beşiktaş', 'Sarıyer', 'Üsküdar', 'Bakırköy', 'Şişli', 'Beyoğlu', 'Fatih'] },
  { city: 'Ankara', districts: ['Çankaya', 'Keçiören', 'Mamak', 'Etimesgut', 'Yenimahalle'] },
  { city: 'Izmir', districts: ['Konak', 'Karşıyaka', 'Bornova', 'Buca', 'Alsancak'] },
  { city: 'Antalya', districts: ['Muratpaşa', 'Konyaaltı', 'Lara', 'Kepez'] },
  { city: 'Bursa', districts: ['Nilüfer', 'Osmangazi', 'Yıldırım', 'Mudanya'] },
];

const BUILDING_TYPES = ['apartment', 'detached', 'semi-detached', 'villa'];
const STREET_NAMES = [
  'Atatürk Cad.', 'Cumhuriyet Blv.', 'İstiklal Sk.', 'Barış Manço Sk.',
  'Yeşilçam Cd.', 'Bağdat Cad.', 'Sakıp Sabancı Cd.', 'Fenerbahçe Sk.',
  'Çiçek Pasajı Sk.', 'Galata Cd.', 'Nişantaşı Cd.', 'Bebek Cd.',
];

const COMPONENT_TYPES = ['window', 'door', 'facade', 'roof', 'balcony', 'insulation', 'solar_panel'];

function generateAddress(): string {
  const street = pick(STREET_NAMES);
  const no = randomInt(1, 120);
  return `${street} No:${no}`;
}

function generateDetections(): object[] {
  const count = randomInt(3, 8);
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    class: pick(COMPONENT_TYPES),
    confidence: randomFloat(0.72, 0.98, 3),
    bbox: [randomInt(10, 200), randomInt(10, 200), randomInt(250, 600), randomInt(250, 600)],
    area_px: randomInt(5000, 80000),
  }));
}

function generateComponents(): object[] {
  const components = ['window', 'facade', 'roof', 'door'];
  return components.map((type) => ({
    component: type,
    u_value: randomFloat(0.8, 3.5, 2),
    area_m2: randomFloat(2, 50, 1),
    material: pick(['PVC', 'aluminum', 'wood', 'brick', 'concrete', 'EPS', 'XPS', 'glass_wool']),
    condition: pick(['good', 'fair', 'poor']),
  }));
}

function generateRenovations(): object[] {
  return [
    {
      component: 'window',
      suggestion: 'Replace single-glazed windows with triple-glazed low-E windows',
      estimated_saving_pct: randomFloat(15, 30),
      estimated_cost_eur: randomInt(3000, 8000),
      priority: 'high',
    },
    {
      component: 'facade',
      suggestion: 'Apply 12cm EPS external wall insulation',
      estimated_saving_pct: randomFloat(20, 40),
      estimated_cost_eur: randomInt(5000, 15000),
      priority: 'high',
    },
    {
      component: 'roof',
      suggestion: 'Add 20cm glass wool roof insulation',
      estimated_saving_pct: randomFloat(10, 25),
      estimated_cost_eur: randomInt(2000, 6000),
      priority: 'medium',
    },
    {
      component: 'door',
      suggestion: 'Install insulated steel entrance door',
      estimated_saving_pct: randomFloat(3, 8),
      estimated_cost_eur: randomInt(800, 2500),
      priority: 'low',
    },
  ];
}

// ── Main Seed Function ──────────────────────────────────────

async function main() {
  console.log('🌱 Starting GreenValue AI database seed...\n');

  // Clean existing data (order matters for FK constraints)
  console.log('🗑️  Cleaning existing data...');
  await prisma.auditLog.deleteMany();
  await prisma.report.deleteMany();
  await prisma.analysis.deleteMany();
  await prisma.property.deleteMany();
  await prisma.user.deleteMany();
  console.log('   Done.\n');

  // ── 1. Create Users ──────────────────────────────────────
  console.log('👤 Creating users...');
  const hashedPassword = await bcrypt.hash('Test1234!', 10);

  const adminUser = await prisma.user.create({
    data: {
      email: 'admin@greenvalue.ai',
      password: hashedPassword,
      fullName: 'Erdinç Erdoğan',
      phone: '+90 532 000 0001',
      role: Role.ADMIN,
      isActive: true,
      lastLogin: daysAgo(0),
    },
  });

  const ownerUsers = await Promise.all(
    [
      { email: 'mehmet.yilmaz@example.com', fullName: 'Mehmet Yılmaz', phone: '+90 533 100 0001' },
      { email: 'ayse.kaya@example.com', fullName: 'Ayşe Kaya', phone: '+90 534 200 0002' },
      { email: 'ali.demir@example.com', fullName: 'Ali Demir', phone: '+90 535 300 0003' },
      { email: 'fatma.celik@example.com', fullName: 'Fatma Çelik', phone: '+90 536 400 0004' },
      { email: 'emre.ozturk@example.com', fullName: 'Emre Öztürk', phone: '+90 537 500 0005' },
      { email: 'zeynep.arslan@example.com', fullName: 'Zeynep Arslan', phone: '+90 538 600 0006' },
    ].map((u) =>
      prisma.user.create({
        data: {
          ...u,
          password: hashedPassword,
          role: Role.OWNER,
          isActive: true,
          lastLogin: daysAgo(randomInt(0, 14)),
        },
      }),
    ),
  );

  const contractorUsers = await Promise.all(
    [
      { email: 'contractor.hasan@example.com', fullName: 'Hasan Usta', phone: '+90 539 700 0007' },
      { email: 'yapi.insaat@example.com', fullName: 'Yapı İnşaat Ltd.', phone: '+90 540 800 0008' },
    ].map((u) =>
      prisma.user.create({
        data: {
          ...u,
          password: hashedPassword,
          role: Role.CONTRACTOR,
          isActive: true,
          lastLogin: daysAgo(randomInt(0, 7)),
        },
      }),
    ),
  );

  const allUsers = [adminUser, ...ownerUsers, ...contractorUsers];
  console.log(`   Created ${allUsers.length} users.\n`);

  // ── 2. Create Properties ─────────────────────────────────
  console.log('🏠 Creating properties...');
  const properties: any[] = [];

  for (const owner of ownerUsers) {
    const propCount = randomInt(1, 3);
    for (let i = 0; i < propCount; i++) {
      const cityData = pick(TURKISH_CITIES);
      const prop = await prisma.property.create({
        data: {
          title: `${pick(BUILDING_TYPES).charAt(0).toUpperCase() + pick(BUILDING_TYPES).slice(1)} - ${cityData.city}`,
          address: generateAddress(),
          city: cityData.city,
          district: pick(cityData.districts),
          postalCode: `${randomInt(10000, 99999)}`,
          latitude: randomFloat(36.0, 42.0, 6),
          longitude: randomFloat(26.0, 44.0, 6),
          buildingYear: randomInt(1970, 2023),
          buildingType: pick(BUILDING_TYPES),
          floorArea: randomFloat(60, 300, 1),
          floors: randomInt(1, 12),
          units: randomInt(1, 24),
          description: `A well-maintained ${pick(BUILDING_TYPES)} property in ${cityData.city}.`,
          ownerId: owner.id,
        },
      });
      properties.push(prop);
    }
  }
  console.log(`   Created ${properties.length} properties.\n`);

  // ── 3. Create Analyses ────────────────────────────────────
  console.log('🔬 Creating analyses...');
  const analyses: any[] = [];
  const energyLabels: EnergyLabel[] = [
    EnergyLabel.A_PLUS, EnergyLabel.A, EnergyLabel.B, EnergyLabel.C,
    EnergyLabel.D, EnergyLabel.E, EnergyLabel.F, EnergyLabel.G,
  ];

  for (const prop of properties) {
    const analysisCount = randomInt(1, 3);
    for (let i = 0; i < analysisCount; i++) {
      const status = pick([
        AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED,
        AnalysisStatus.PENDING, AnalysisStatus.PROCESSING, AnalysisStatus.FAILED,
      ]);

      const isCompleted = status === AnalysisStatus.COMPLETED;
      const jobId = `bull-${randomUUID().slice(0, 8)}`;

      const analysis = await prisma.analysis.create({
        data: {
          jobId,
          status,
          imageKey: `raw-uploads/${prop.id}/${randomUUID().slice(0, 8)}.jpg`,
          heatmapKey: isCompleted ? `ai-heatmaps/${prop.id}/${randomUUID().slice(0, 8)}_heatmap.png` : null,
          detections: isCompleted ? generateDetections() : Prisma.JsonNull,
          inferenceTimeMs: isCompleted ? randomFloat(120, 850) : null,
          overallUValue: isCompleted ? randomFloat(0.8, 3.2) : null,
          energyLabel: isCompleted ? pick(energyLabels) : null,
          components: isCompleted ? generateComponents() : Prisma.JsonNull,
          renovations: isCompleted ? generateRenovations() : Prisma.JsonNull,
          modelVersion: isCompleted ? 'yolo11m-seg' : null,
          device: isCompleted ? 'cuda' : null,
          pipelineTimeMs: isCompleted ? randomFloat(500, 3000) : null,
          errorMessage: status === AnalysisStatus.FAILED ? 'Image quality too low for reliable detection' : null,
          propertyId: prop.id,
          userId: prop.ownerId,
          createdAt: daysAgo(randomInt(0, 60)),
        },
      });
      analyses.push(analysis);
    }
  }
  console.log(`   Created ${analyses.length} analyses.\n`);

  // ── 4. Create Reports ─────────────────────────────────────
  console.log('📄 Creating reports...');
  const completedAnalyses = analyses.filter((a) => a.status === AnalysisStatus.COMPLETED);
  let reportCount = 0;

  for (const analysis of completedAnalyses) {
    // ~70% of completed analyses get a report
    if (Math.random() > 0.3) {
      await prisma.report.create({
        data: {
          format: pick([ReportFormat.PDF, ReportFormat.PDF, ReportFormat.JSON]),
          fileKey: `pdf-reports/${analysis.propertyId}/${randomUUID().slice(0, 8)}_report.pdf`,
          fileSize: randomInt(200_000, 2_500_000),
          title: `Energy Performance Report — ${new Date(analysis.createdAt).toLocaleDateString('en-GB')}`,
          analysisId: analysis.id,
          propertyId: analysis.propertyId,
          userId: analysis.userId,
        },
      });
      reportCount++;
    }
  }
  console.log(`   Created ${reportCount} reports.\n`);

  // ── 5. Create Audit Logs ──────────────────────────────────
  console.log('📋 Creating audit logs...');
  const auditActions = [
    { action: 'user.login', entity: 'User' },
    { action: 'user.register', entity: 'User' },
    { action: 'property.create', entity: 'Property' },
    { action: 'property.update', entity: 'Property' },
    { action: 'analysis.created', entity: 'Analysis' },
    { action: 'analysis.completed', entity: 'Analysis' },
    { action: 'report.generated', entity: 'Report' },
    { action: 'report.downloaded', entity: 'Report' },
  ];

  const userAgents = [
    'GreenValue-Mobile/1.0 (iOS 17.4)',
    'GreenValue-Mobile/1.0 (Android 14)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
  ];

  const auditLogs: any[] = [];
  for (let i = 0; i < 50; i++) {
    const user = pick(allUsers);
    const auditAction = pick(auditActions);
    const log = await prisma.auditLog.create({
      data: {
        action: auditAction.action,
        entity: auditAction.entity,
        entityId: randomUUID(),
        metadata: { source: pick(['mobile', 'web', 'api']), duration_ms: randomInt(50, 2000) },
        ip: `192.168.${randomInt(1, 254)}.${randomInt(1, 254)}`,
        userAgent: pick(userAgents),
        userId: user.id,
        createdAt: daysAgo(randomInt(0, 90)),
      },
    });
    auditLogs.push(log);
  }
  console.log(`   Created ${auditLogs.length} audit logs.\n`);

  // ── Summary ───────────────────────────────────────────────
  console.log('═══════════════════════════════════════════════════');
  console.log('  ✅ Seed completed successfully!');
  console.log('═══════════════════════════════════════════════════');
  console.log(`  Users:       ${allUsers.length}`);
  console.log(`  Properties:  ${properties.length}`);
  console.log(`  Analyses:    ${analyses.length}`);
  console.log(`  Reports:     ${reportCount}`);
  console.log(`  Audit Logs:  ${auditLogs.length}`);
  console.log('═══════════════════════════════════════════════════');
  console.log('\n  🔑 Login credentials (all users):');
  console.log('     Password: Test1234!');
  console.log('     Admin:    admin@greenvalue.ai');
  console.log('     Owners:   mehmet.yilmaz@example.com, ayse.kaya@example.com, ...');
  console.log('═══════════════════════════════════════════════════\n');
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
