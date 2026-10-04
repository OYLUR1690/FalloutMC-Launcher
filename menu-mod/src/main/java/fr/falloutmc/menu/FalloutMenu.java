package fr.falloutmc.menu;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.options.OptionsScreen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import net.minecraft.network.chat.Component;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.ScreenEvent;

@Mod(value = "falloutmc_menu", dist = Dist.CLIENT)
public final class FalloutMenu {
    private static final String ADDRESS = "116.202.116.207:25565";
    public FalloutMenu() {
        NeoForge.EVENT_BUS.addListener(this::opening);
    }
    private void opening(ScreenEvent.Opening event) {
        if (event.getNewScreen() instanceof TitleScreen) {
            event.setNewScreen(new FalloutScreen());
        }
    }
    private static final class FalloutScreen extends Screen {
        FalloutScreen() { super(Component.literal("FalloutMC")); }
        @Override protected void init() {
            int x = width / 2 - 110;
            int y = height / 2 - 12;
            addRenderableWidget(Button.builder(Component.literal("Rejoindre FalloutMC"), button -> {
                Minecraft mc = Minecraft.getInstance();
                ServerData server = new ServerData("FalloutMC", ADDRESS, ServerData.Type.OTHER);
                ConnectScreen.startConnecting(this, mc, ServerAddress.parseString(ADDRESS), server, false, null);
            }).bounds(x, y, 220, 24).build());
            addRenderableWidget(Button.builder(Component.literal("Options"), button ->
                minecraft.setScreen(new OptionsScreen(this, minecraft.options))
            ).bounds(x, y + 32, 220, 24).build());
            addRenderableWidget(Button.builder(Component.literal("Quitter"), button -> minecraft.stop())
                .bounds(x, y + 64, 220, 24).build());
        }
        @Override public boolean shouldCloseOnEsc() { return false; }
        @Override public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
            graphics.fill(0, 0, width, height, 0xFF111A15);
            graphics.drawCenteredString(font, "FALLOUTMC", width / 2, height / 2 - 65, 0xB3EB72);
            graphics.drawCenteredString(font, "Survis. Explore. Reconstruis.", width / 2, height / 2 - 43, 0xC5D9C5);
            graphics.drawCenteredString(font, "Authentification EasyLogin en jeu", width / 2, height - 25, 0x829582);
            super.render(graphics, mouseX, mouseY, partialTick);
        }
    }
}
