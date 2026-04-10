"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import api, { type Settings } from "@/lib/api";
import {
  Check,
  Eye,
  EyeOff,
  Key,
  Loader2,
  MessageSquare,
  Save,
  SendHorizontal,
  Tag,
  Wallet,
  Globe,
  X,
} from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [anthropicKey, setAnthropicKey] = useState("");
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [telegramToken, setTelegramToken] = useState("");
  const [showTelegramToken, setShowTelegramToken] = useState(false);
  const [telegramChatId, setTelegramChatId] = useState("");
  const [devtoKey, setDevtoKey] = useState("");
  const [showDevtoKey, setShowDevtoKey] = useState(false);
  const [nicheTopics, setNicheTopics] = useState<string[]>([]);
  const [customKeywords, setCustomKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [dailyBudget, setDailyBudget] = useState("10");
  const [monthlyBudget, setMonthlyBudget] = useState("300");
  const [autoDowngrade, setAutoDowngrade] = useState(true);
  const [publishMode, setPublishMode] = useState("draft");

  const TOPIC_OPTIONS = [
    "Blockchain",
    "Autonomous Vehicles",
    "AI/ML Systems",
    "IoT Security",
    "Federated Learning",
    "Zero-Knowledge Proofs",
    "Edge Computing",
    "Smart Contracts",
  ];

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setSettings(s);
        setTelegramChatId(s.telegram_chat_id || "");
        setNicheTopics(s.niche_topics || []);
        setCustomKeywords(s.custom_keywords || []);
        setDailyBudget(String(s.daily_budget_usd));
        setMonthlyBudget(String(s.monthly_budget_usd));
        setAutoDowngrade(s.auto_downgrade);
        setPublishMode(s.default_publish_mode || "draft");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        niche_topics: nicheTopics,
        custom_keywords: customKeywords,
        daily_budget_usd: parseFloat(dailyBudget),
        monthly_budget_usd: parseFloat(monthlyBudget),
        auto_downgrade: autoDowngrade,
        default_publish_mode: publishMode,
        telegram_chat_id: telegramChatId,
      };
      if (anthropicKey) payload.anthropic_api_key = anthropicKey;
      if (telegramToken) payload.telegram_bot_token = telegramToken;
      if (devtoKey) payload.devto_api_key = devtoKey;

      await api.updateSettings(payload as Partial<Settings>);
      toast.success("Settings saved successfully");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const toggleTopic = (topic: string) => {
    setNicheTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const addKeyword = () => {
    const kw = newKeyword.trim();
    if (kw && !customKeywords.includes(kw)) {
      setCustomKeywords((prev) => [...prev, kw]);
      setNewKeyword("");
    }
  };

  const removeKeyword = (kw: string) => {
    setCustomKeywords((prev) => prev.filter((k) => k !== kw));
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">Configure your Quorum instance</p>
      </div>

      <Tabs defaultValue="api-keys">
        <TabsList className="flex flex-wrap">
          <TabsTrigger value="api-keys">
            <Key className="mr-1.5 h-3.5 w-3.5" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="topics">
            <Tag className="mr-1.5 h-3.5 w-3.5" />
            Topics
          </TabsTrigger>
          <TabsTrigger value="budget">
            <Wallet className="mr-1.5 h-3.5 w-3.5" />
            Budget
          </TabsTrigger>
          <TabsTrigger value="publishing">
            <Globe className="mr-1.5 h-3.5 w-3.5" />
            Publishing
          </TabsTrigger>
        </TabsList>

        {/* API Keys */}
        <TabsContent value="api-keys" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Anthropic API Key</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showAnthropicKey ? "text" : "password"}
                    placeholder={settings?.anthropic_api_key_set ? "sk-ant-•••••••••" : "sk-ant-api03-..."}
                    value={anthropicKey}
                    onChange={(e) => setAnthropicKey(e.target.value)}
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                  >
                    {showAnthropicKey ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Status:</span>
                {settings?.anthropic_api_key_set ? (
                  <Badge variant="secondary" className="bg-green-500/15 text-green-700 dark:text-green-400">
                    <Check className="mr-1 h-3 w-3" />
                    Connected
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="bg-zinc-500/15 text-zinc-600">
                    Not configured
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications */}
        <TabsContent value="notifications" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Telegram Notifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Bot Token</Label>
                <div className="relative">
                  <Input
                    type={showTelegramToken ? "text" : "password"}
                    placeholder={settings?.telegram_bot_token_set ? "•••••••••" : "Enter bot token"}
                    value={telegramToken}
                    onChange={(e) => setTelegramToken(e.target.value)}
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowTelegramToken(!showTelegramToken)}
                  >
                    {showTelegramToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Chat ID</Label>
                <Input
                  placeholder="123456789"
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                />
              </div>
              <Button variant="outline" size="sm">
                <SendHorizontal className="mr-2 h-4 w-4" />
                Send Test Message
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Topics */}
        <TabsContent value="topics" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Research Topics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label>Niche Topics</Label>
                <div className="grid grid-cols-2 gap-2">
                  {TOPIC_OPTIONS.map((topic) => (
                    <label
                      key={topic}
                      className="flex items-center gap-2 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={nicheTopics.includes(topic)}
                        onChange={() => toggleTopic(topic)}
                        className="rounded border-input"
                      />
                      {topic}
                    </label>
                  ))}
                </div>
              </div>
              <Separator />
              <div className="space-y-3">
                <Label>Custom Keywords</Label>
                <div className="flex flex-wrap gap-2">
                  {customKeywords.map((kw) => (
                    <Badge key={kw} variant="secondary" className="gap-1">
                      {kw}
                      <button
                        type="button"
                        onClick={() => removeKeyword(kw)}
                        className="ml-1 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="Add keyword..."
                    value={newKeyword}
                    onChange={(e) => setNewKeyword(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
                  />
                  <Button variant="outline" size="sm" onClick={addKeyword}>
                    Add
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Budget */}
        <TabsContent value="budget" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Budget Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Daily Limit (USD)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={dailyBudget}
                    onChange={(e) => setDailyBudget(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Monthly Limit (USD)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={monthlyBudget}
                    onChange={(e) => setMonthlyBudget(e.target.value)}
                  />
                </div>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Auto-downgrade Models</Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Automatically use cheaper models when budget is low
                  </p>
                </div>
                <Switch checked={autoDowngrade} onCheckedChange={setAutoDowngrade} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Publishing */}
        <TabsContent value="publishing" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">dev.to Publishing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>API Key</Label>
                <div className="relative">
                  <Input
                    type={showDevtoKey ? "text" : "password"}
                    placeholder={settings?.devto_api_key_set ? "•••••••••" : "Enter dev.to API key"}
                    value={devtoKey}
                    onChange={(e) => setDevtoKey(e.target.value)}
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowDevtoKey(!showDevtoKey)}
                  >
                    {showDevtoKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Default Publish Mode</Label>
                <Select value={publishMode} onValueChange={(v) => v && setPublishMode(v)}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="live">Live</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save Settings
        </Button>
      </div>
    </div>
  );
}
